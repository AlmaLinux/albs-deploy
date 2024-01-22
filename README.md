# Quick Deployment
You can deploy build system in a really fast way. Let's get started.

### Requirements
* Ansible version is 2.10 or newer
* Ansible community.docker collection
* Docker compose V2
* Python3 & PyJWT==2.7.0 & requests==2.25.1

### Steps
* Create deployment scripts local copy.
  ```sh
  git clone git@github.com:AlmaLinux/albs-deploy.git
  cd albs-deploy
  ```
* Create `vars.yml` in repository root with the following content.
  ```yml
  ---
  github_client: <OAuth client id>
  github_client_secret: <OAuth token>
  immudb_username: <immudb username to be used>
  immudb_password: <immudb password to be used>
  immudb_database: <immudb database name to be used>
  immudb_address: <url in format `host:port` of immudb instance, default port is 3322>
  immudb_public_key_file: <path of the public key to use>
  frontend_baseurl: http://<Preferred hostname or IP address>:8080
  ```
  if you want deploy build system on remote machine add the following parameters.
  ```yml
  albs_address: <Machine IP address>
  use_local_connection: false
  ```
* Install ansible plugins and run deployment
  ```sh
  ansible-galaxy install -r requirements.yml
  ansible-playbook -i inventories/one_vm -vv -u <user> -e "@vars.yml" playbooks/albs_on_one_vm.yml
  ```
* If you're getting the following error on DEB based distros set `ansible_python_interpreter` var to your python location
  ```E: Package 'python-apt' has no installation candidate```
  https://stackoverflow.com/questions/51622712/ansible-requires-python-apt-but-its-already-installed

## Clean VM preparation
```sh
adduser albs
passwd albs
usermod -aG wheel albs
echo "albs ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
```
If you're on RPM based distro (ex: CentOS 8.5):
```sh
yum install -y yum-utils
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install docker-ce docker-ce-cli docker-compose-plugin containerd.io python3
```
Or DEB based distro (ex: Debian 11.7):
```sh
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release python3 python3-pip
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -
echo "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io
```
Install another dependencies and run docker:
```sh
pip3 install PyJWT requests
systemctl start docker
systemctl enable docker
usermod -aG docker albs
su - albs
```

## Modifying
### A new service's config
* Add template to `roles/dev_deploy/templates` for config of a service. The name of file should be as `<name_of_target_config_file>.j2`
* Add description of a config to `roles/dev_deploy/defaults/main/configs.yml`

### A new directory
* Add description to `roles/dev_deploy/defaults/main/common.yml`

## How to get tokens?
Several tokens you can get on separate resources.
### GitHub OAuth Tokens (github_client_secret & github_client)
1. Login to your GitHub account.
2. Navigate to `Settings > Developer Settings > OAuth Apps`.
3. Click `New OAuth App`.
4. Fill in the form with appropriate details: `Application Name`, `Homepage URL`, and `Authorization callback URL`. 
5. The `Homepage URL` field is `http://<Preferred hostname or IP address>:8080`.
6. The `Authorization callback URL` field is `http://<Preferred hostname or IP address>:8080/api/v1/auth/github/callback`.
7. Click `Register application`.
8. On the next page, your `Client ID` and `Client Secret` will be visible. Note them down, but keep them secure.

### Immudb Tokens

1. Username: Use the default username (`immudb`) or create your own user via [immudb-wrapper](https://github.com/AlmaLinux/immudb-wrapper) or [immuadmin](https://docs.immudb.io/master/connecting/clitools.html#immuadmin) tool
2. Password: Use the default password (`immudb`) for the `immudb` user or use the password from your created user.
3. Database: Use the default database (`defaultdb`) or create your own database via [immudb-wrapper](https://github.com/AlmaLinux/immudb-wrapper) or [immuadmin]

### JWT Tokens
They are generated automatically, but if you want to make them static, it makes sense to generate them manually.
You can use scripts for generation from here: `roles/dev_deploy/tasks/common.yml`. 
Be noticed that ALBS and ALTS tokens have different payload.

#### ALBS Token
This token has the following payload:
```json
{
   "sub":"1",
   "aud":[
      "fastapi-users:auth"
   ],
   "exp":1777628461
}
```
#### ALTS Token
For this token type payload is different:
```json
{
   "email":"base_user@almalinux.org"
}
```

## What else vars exist?
`vars.yml` can contain extended set of variables. The most vars defaults you can see here `inventories/one_vm/group_vars/all.yml` 
Please consider the following description:

```yaml
use_local_connection: true|false <up docker containers on a host machine>
use_already_cloned_repos: true|false <use local sources from already cloned repos>
local_sources_root: <folder with cloned repositories; can be empty if you use cloning of sources from GH>
local_volumes_root: <folder with mounts for docker containers; can be empty if you use cloning of sources from GH>
ansible_interpreter_path: <path to python interpreter on a destination host>

# playbook generates a key itself if the var is empty
pgp_keys:
    - <last_16_digits_of_keys_fingerprint>

alts_jwt_token: <If you have generated JWT token manually set it here>
albs_jwt_token: <If you have generated JWT token manually set it here>
albs_jwt_secret: <Secret of yours generated token>
alts_jwt_secret: <Secret of yours generated token>


```
Of course, you can override the service's default users, passwords and rabbitmq params.
```yaml
postgres_password:
postgres_db:
postgres_user:

rabbitmq_erlang_cookie:
rabbitmq_user:
rabbitmq_pass:
rabbitmq_vhost:

pulp_password:
```

## Contributing to albs-deploy
Any question? Found a bug? File an [issue](https://github.com/AlmaLinux/build-system/issues).
Do you want to contribute with source code?
1. Fork the repository on GitHub
2. Create a new feature branch
3. Write your change
4. Submit a pull request
