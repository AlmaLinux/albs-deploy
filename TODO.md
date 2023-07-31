1. Exclude clone/sync the build node sources in the role `dev_deploy`
2. Add path to requirements.txt in the task `separate_build_node/create_env`
3. Add clone/sync task to role `separate_build_node`
4. Installation of `buildnode.repo` to `/etc/yum.repo.d`
5. 