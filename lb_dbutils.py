"""
' lb_dbutils.py
'
' A thin layer on top of psycopg2 to run queries against the LUMO back end.
"""

import psycopg2
import psycopg2.extras
import StringIO
from psycopg2.extensions import STATUS_READY

#==================================================================================================
class Lumodb:
#==================================================================================================
  """ Our own artisan connection pooling. Each process can only have one instance of each of the five
  connection types. We don't do multiple threads. The connections are reused as long as they are
  good. """
  conn = None
  def __init__ (self, dbname, scan_disabled=False):
    """ Establishes the connection with the backend databases. """
    try:
      self.dbname = dbname
      if dbname == 'rds-admin':
        if Lumodb.conn:
          if Lumodb.conn.status == STATUS_READY:
            self.__conn = Lumodb.conn
            return
          else:
            Lumodb.conn.close()
            Lumodb.conn = None
        # follower database credentials (YELLOW)
        self.__DB_HOST = "lumocha-postgresql.ck4vbjenwmdo.us-west-2.rds.amazonaws.com"
        self.__DB_NAME = "lumocha_postgresql"
        self.__DB_USER = "chavli"
        self.__DB_PORT = 5432
        self.__DB_PASS = "03QlXiZ1415&"
        self.__conn = psycopg2.connect("dbname=%s user=%s password=%s host=%s port=%d"
                                       % (self.__DB_NAME, self.__DB_USER,self.__DB_PASS,
                                        self.__DB_HOST, self.__DB_PORT ))
        self.__conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        Lumodb.conn = self.__conn
      else:
        Lumodb.conn = None
    except Exception, e:
      perr (str(e))
      raise

  # Destructor
  #-------------------
  def __del__(self):
  #-------------------
    pass

  #-------------------
  def disconnect(self):
  #-------------------
    pass

  # insert
  #
  # Performs a single, or multiple, insert operation(s) on the given table with the given data.
  # The query is handled as a prepared statement so multi-inserts are more efficient.
  #
  # arguments:
  #   table: table name
  #   data: a list of dictionaries where each element is a row
  #   unique_cols: A list of columns that must be unique in the target table. This is checked
  #                 in the insert statement and may be slow.
  #
  # returns: the number of rows inserted
  #
  #-------------------
  def insert (self, table, data, unique_cols=[]):
  #-------------------
    if not self.__conn:
        return None

    num_inserted = 0
    if len(data) == 0: return 0

    columns = "("
    params = ""
    # assume all new rows have the same columns
    for col in data[0].keys():
      columns += str(col) + ","
      params += "%s,"

    # Build the where clause to avoid duplicates
    where = ''
    if unique_cols:
      where = ' where not exists (select 1 from ' + table + ' where '
      first = True
      for ucol in unique_cols:
        if not first:
          where += ' and '
        else:
          first = False
        where += (ucol + ' = %s ')
      where += ')'

    columns = colums[0:-1]
    params = params[0:-1]

    # the query
    query = "INSERT INTO " + table + " " + columns + " SELECT "\
      + params + where

    # insert all the given data
    curs = self.__conn.cursor()
    for row in data:
      try:
        # Pick the unique values
        unique_vals = []
        for ucol in unique_cols:
          unique_vals = list (row[k] for k in unique_cols)
        curs.execute(query, tuple(row.values()) + tuple(unique_vals))
        num_inserted += 1
        if num_inserted % 100 == 0 :
          self.__conn.commit()
      except Exception, e:
        self.__conn.commit()
        pexc("%s row: %s",str(e) + str(row))
        curs.close()
        return num_inserted
    self.__conn.commit()
    curs.close()

    return num_inserted

  # Just like insert, except we use the postgres COPY function into a temp table to speed things
  # up. Returns number of rows inserted on success, 0 on failure
  #-------------------
  def insert_bulk (self, table, data, unique_cols=[]):
  #-------------------
    if not self.__conn:
        return None

  # The keys of the first dictionary in data are the column names we need
    if not data:
      perr ('no rows to insert')
      return 0

    try:
      # Put the data into a string file-like object, in csv format
      csv = StringIO.StringIO()
      for row in data:
        # Strip all strings in values() and put them into a semicol del string
        tstr = ";".join ([str(x).strip() for x in row.values()]) + "\n"
        csv.write (tstr)
      # Make a temp table to hold the imported data
      cols = data[0].keys();
      temptable = table + '_bulk'
      sql = 'create temporary table ' + temptable
      sql += ' as select ' + ",".join(cols) + ' from ' + table + ' where 1=0'
      self.executeWriteQuery (sql)

      # Bulk load the stringio into the temp table
      curs = self.__conn.cursor()
      csv.seek(0)
      curs.copy_expert("COPY " + temptable + " FROM STDIN WITH NULL AS 'None' DELIMITER ';'", csv)
      self.__conn.commit()
      curs.close()

      # Delete duplicates from target table if unique_cols specified
      distinct = ' distinct '
      if unique_cols:
        colstr = ','.join (unique_cols)
        distinct = ' distinct on ( ' + colstr + ' ) '
        plog ('deleting duplicate ' + colstr + ' from ' + table)
        where = ' where (' + colstr + ') in (select ' + colstr + ' from ' + temptable + ')'
        sql = 'delete from ' + table + where
        plog ('delete query: ' + sql)
        n_deleted = self.executeWriteQuery (sql)
        if n_deleted > 0:
          perr ('Deleted %d duplicates in %s' % (n_deleted,table))

      # Insert new rows into target
      sql = "insert into %s(%s) select %s  * from %s" % (table, ",".join(cols), distinct, temptable)
      plog ('insert query: ' + sql)
      return self.executeWriteQuery (sql)
    except Exception as e:
      pexc(e)
      return 0

  # Executes an SQL query and returns the rows as a list of tuples
  #-------------------
  def executeReadQuery (self, query, args=()):
  #-------------------
    if not self.__conn:
        return None

    rows = None
    curs = self.__conn.cursor()
    try:
      # print query
      curs.execute (query, args)
      rows = curs.fetchall()
    except Exception, e:
      raise
    finally:
      curs.close()
    return rows

  # Executes an SQL query and returns an iterator giving the rows as tuples.
  # Useful for large data sets if you don't want to cram them into memory at once.
  #-------------------
  def executeReadQueryIter (self, query, args=()):
  #-------------------
    if not self.__conn:
        return None

    curs = self.__conn.cursor('mycurs')
    try:
      # print query
      curs.execute (query, args)
      return curs
    except Exception, e:
      raise

  #-------------------
  def executeReadQueryIterHash(self, query, args=()):
  #-------------------
    if not self.__conn:
        return None

    curs = self.__conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    try:
      curs.execute(query, args)
      return curs;
    except Exception, e:
      raise


  # Get SQL output into a list of hashes (one hash per row).
  # Also returns a list with the column names in order.
  #-------------------------------
  def executeReadQueryHash (self, query, args=()):
  #-------------------------------
    if not self.__conn:
        return None

    rows = None
    curs = self.__conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    try:
      curs.execute (query, args)
      rows = curs.fetchall()
    except Exception, e:
      raise
    finally:
      curs.close()
    # Get the columns
    if len(rows) == 0: return (None,None)
    colnames = rows[0].keys();
    return (rows,colnames)

  # executeWriteQuery
  #
  # Executes a custom SQL query which modifies data in the database.
  #
  # arguments:
  #   query - a string representing the SQL query to be executed. %s placeholders for arg values
  #   args  - a tuple with the arg values
  #
  # example: executeWriteQuery ('insert into tt values(%s,%s)',(13,'tom'))
  # returns:
  #   Number of affected rows
  #
  #-------------------
  def executeWriteQuery(self, query, args=()):
  #-------------------
    if not self.__conn:
        return None

    curs = self.__conn.cursor()
    try:
      curs.execute (query,args)
      self.__conn.commit()
      return curs.rowcount
    except Exception, e:
      raise
    finally:
      curs.close()
