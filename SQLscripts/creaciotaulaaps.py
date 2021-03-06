import psycopg2
from psycopg2 import Error


try:
    connection = psycopg2.connect(user = "",
                                  password = "",
                                  host = "",
                                  port = "",
                                  database = "")

    cursor = connection.cursor()


    create_table_query = '''CREATE TABLE tfmpausalasapinformacioAP
                  (apmac TEXT NOT NULL,
                   name TEXT NOT NULL,
                  latitud FLOAT NOT NULL,
                  longitud FLOAT NOT NULL,
                  zonaname TEXT NOT NULL,
                  PRIMARY KEY (apmac),
                  FOREIGN KEY (zonaname) REFERENCES tfmpausalastaulazona(zonaname) ); '''



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
