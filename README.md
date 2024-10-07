# perun-negotiator-sync
Service to synchronize access rights from the Perun Identity Management System into the BBMRI-ERIC Negotiator.



## Testing
start the negotiator test docker with the mock oidc server

```bash
docker compose -f test-docker/compose.yaml up -d
```


```bash
bash .github/scripts/update_users_test.sh
```

## Run the negotiator sync

 ```bash
 python src/bbmri_negotiator.py resources/test_negotiator.json 
 ```
