#!/bin/bash -e

ACCESS_TOKEN=$(curl -s -d 'grant_type=client_credentials' -u 123:123 http://localhost:4011/connect/token | jq -r .access_token)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "Missing access token"
  exit 1;
fi

BASE="http://localhost:8081/api/v3/users"

# Function to check the length of resources and HTTP status
check_resources() {
  local url=$1
  local expected_length=$2

  # Make the request and capture the HTTP status code
  response=$(curl -s -w "%{http_code}" --oauth2-bearer "$ACCESS_TOKEN" "$url")
  http_status="${response: -3}"
  response_body="${response%???}"

  # Check if the HTTP status is 200
  if [ "$http_status" -eq 200 ]; then
    # Extract the length of resources using jq
    length=$(echo "$response_body" | jq '.["_embedded"]["resources"] | length')

    # Check if the length matches the expected value
    if [ "$length" -ne "$expected_length" ]; then
      echo "Error: Resource length at $url is $length, expected $expected_length"
      exit 1
    else
      echo "Resource length at $url is correct: $length"
    fi
  else
    echo "Request to $url failed with status: $http_status"
    exit 1
  fi
}


# Check both URLs
check_resources "${BASE}/1/resources" 1
check_resources "${BASE}/2/resources" 0


