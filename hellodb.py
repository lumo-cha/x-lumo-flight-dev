import lb_dbutils

db_conn = lb_dbutils.Lumodb("rds-admin")
rows, colnames = db_conn.executeReadQueryHash("select * from flight_friends")
if rows:
    for row in rows:
        print (row)
        
