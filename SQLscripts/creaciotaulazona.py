import psycopg2
from psycopg2 import Error


try:
    connection = psycopg2.connect(user = "postgres",
                                  password = "pass@#29",
                                  host = "127.0.0.1",
                                  port = "5432",
                                  database = "postgres_db")

    cursor = connection.cursor()


    create_table_query = '''CREATE TABLE tfmpausalastaulazona
                  (zonaname TEXT NOT NULL,
                  zonanombre TEXT NOT NULL,
                  latitudmaxima FLOAT NOT NULL,
                  longitudmaxima FLOAT NOT NULL,
                  latitudminima FLOAT NOT NULL,
                  longitudminima FLOAT NOT NULL,
                  PRIMARY KEY (zonaname) ); '''



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
