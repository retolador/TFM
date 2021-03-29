import psycopg2
from psycopg2 import Error


try:
    connection = psycopg2.connect(user = "postgres",
                                  password = "pass@#29",
                                  host = "127.0.0.1",
                                  port = "5432",
                                  database = "postgres_db")

    cursor = connection.cursor()


    create_table_query = '''CREATE TABLE tfmpausalastaularegles
                  (idregla INT NOT NULL AUTO_INCREMENT,
                    date TEXT NOT NULL,
                    antecedent TEXT NOT NULL,
                    consequent TEXT NOT NULL,
                    antecedent_support FLOAT NOT NULL,
                    consequent_support FLOAT NOT NULL,
                    support FLOAT NOT NULL,
                    confidence FLOAT NOT NULL,
                    lift FLOAT NOT NULL,
                    leverage FLOAT NOT NULL,
                    conviction FLOAT NOT NULL,
                    PRIMARY KEY (idregla),
                    FOREIGN KEY (consequent) REFERENCES tfmpausalastaulazona(zonaname) ); '''

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
