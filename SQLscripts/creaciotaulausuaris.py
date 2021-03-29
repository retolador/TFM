import psycopg2
from psycopg2 import Error

try:
    connection = psycopg2.connect(user = "",
                                  password = "",
                                  host = "",
                                  port = "",
                                  database = "")

    cursor = connection.cursor()

    create_table_query = '''CREATE TABLE tfmpausalasclassificaciousuaris
          (clientmac    TEXT          NOT NULL,
          date          TEXT      NOT NULL,
          class_hab_esp         TEXT      NOT NULL,
          class_est_mob         TEXT      NOT NULL,
          transport             TEXT      NOT NULL,
          PRIMARY KEY (clientmac,date)
          ); '''


    cursor.execute(create_table_query)
    connection.commit()
    print("Table created successfully in PostgreSQL ")

except (Exception, psycopg2.DatabaseError) as error :
    print ("Error while creating PostgreSQL table", error)
finally:
    #closing database connection.
        if(connection):
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
