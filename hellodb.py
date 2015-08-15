import lb_dbutils

db_conn = lb_dbutils.Lumodb("rds-admin")
rows, colnames = db_conn.executeReadQueryHash("select now() as current_time")
if rows:
    print rows[0]["current_time"]
