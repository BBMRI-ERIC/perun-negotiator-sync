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

## Deployment of server
The script must be located in the `/etc/perun/bbmri_negotiator.d/` directory. The configuration file must be located in the `/etc/perun/bbmri_negotiator.d/` directory. 
Clone the repositroy e.g. to `/etc/perun/perun-negotiator-sync` and create a symlink to the script. 

```bash
cd /etc/perun
git clone https://github.com/BBMRI-ERIC/perun-negotiator-sync.git
ln -s /etc/perun/perun-negotiator-sync/src/bbmri_negotiator.py /etc/perun/bbmri_negotiator.d/bbmri_negotiator.py
```
