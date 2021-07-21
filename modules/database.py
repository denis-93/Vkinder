import sqlalchemy

def get_address_postgresdb(username, password, host, port, database):
    address = 'postgresql://' + username + ':' + password + '@' + host + ':' + port + '/' + database
    return address

class Vkinder_db:
    def __init__(self, username, password, host='localhost', port='5432', database='Vkinder'):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.db = get_address_postgresdb(self.username, self.password, self.host, self.port, self.database)
        self.engine = sqlalchemy.create_engine(self.db)
        self.connection = self.engine.connect()

    def create_db(self):
        self.connection.execute("""CREATE TABLE IF NOT EXISTS vk_user(
        	Vk_id varchar(20) PRIMARY KEY,
        	First_name varchar(40) NOT NULL,
        	Last_name varchar(40) NOT NULL,
            Age integer,
        	Sex varchar(1),
        	City varchar(40)
        );
        CREATE TABLE IF NOT EXISTS couple(
            Id serial PRIMARY KEY,
        	Vk_id varchar(20),
        	VK_User_id varchar(20) NOT NULL REFERENCES VK_User(Vk_id),
        	First_name varchar(40) NOT NULL,
        	Last_name varchar(40) NOT NULL,
        	Age integer,
        	Sex varchar(1),
        	City varchar(40)
        );""")

    def insert_vk_user(self, info):
        self.connection.execute(f"""INSERT INTO vk_user(Vk_id, First_name, Last_name, Age, Sex, City)
        VALUES
        ('{info['id']}', '{info['firstname']}', '{info['lastname']}', {info['age']}, {info['sex']}, {info['city']});""")

    def insert_couple(self, info, id):
        self.connection.execute(f"""INSERT INTO couple(Vk_id, VK_User_id, First_name, Last_name, Age, Sex, City)
        VALUES
        ('{info['vk_id']}', '{id}', '{info['firstname']}', '{info['lastname']}', {info['age']}, {info['sex']}, {info['city']});""")