def create_db_user(curr, user, password):
    create_user(curr, user, password)
    set_password(curr, user, password)
    set_permissions(curr, user)


def create_user(db, user, password):
    sql = """DO
    $body$
    BEGIN
       IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '{name}') THEN
          CREATE ROLE {name} LOGIN PASSWORD '{password}';
       END IF;
    END
    $body$""".format(
        name=user, password=password
    )
    db.execute(sql)


def set_password(db, user, password):
    db.execute(f"ALTER USER {user} WITH PASSWORD '{password}'")


def set_permissions(curr, user):
    revoke_all(curr, user)
    if user == "readonly":
        grant_readonly(curr, user)
    else:
        grant_all(curr, user)


def revoke_all(db, user):
    def revoke_all_on(what):
        db.execute(f"REVOKE ALL PRIVILEGES ON ALL {what} IN SCHEMA public FROM {user}")

    revoke_all_on("tables")
    revoke_all_on("sequences")
    revoke_all_on("functions")


def revoke_write_on_protected_tables(db, user, protected_tables):
    def revoke_specific_on(what):
        db.execute(f"REVOKE INSERT, UPDATE, DELETE ON {what} FROM {user}")

    for table in protected_tables:
        revoke_specific_on(table)


def grant_all(db, user):
    def grant_all_on(what):
        db.execute(f"GRANT ALL PRIVILEGES ON ALL {what} IN SCHEMA public TO {user}")

    print(f"  - Granting all permissions to {user}")
    grant_all_on("tables")
    grant_all_on("sequences")
    grant_all_on("functions")


def grant_readonly(db, user):
    print(f"  - Granting readonly permissions to {user}")
    db.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {user}")
