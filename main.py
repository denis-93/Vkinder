from modules.vkinder import VKinder
from modules.database import Vkinder_db

if __name__ == '__main__':
    database = Vkinder_db('login', 'password')
    database.create_db()
    vk_bot = VKinder()
    vk_bot.start_bot(database)