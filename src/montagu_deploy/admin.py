from constellation.docker_util import return_logs_and_remove


def add_user(cfg, name, username, email, password):
    args = ["add", name, username, email, password, "--if-not-exists"]
    return run(cfg, args)


def add_role_to_user(cfg, name, role):
    args = ["addRole", name, role]
    return run(cfg, args)


def add_user_to_group(cfg, username, modelling_group):
    args = ["addUserToGroup", username, modelling_group]
    return run(cfg, args)


def run(cfg, args):
    image = str(cfg.images["api_admin"])
    return return_logs_and_remove(image, args)
