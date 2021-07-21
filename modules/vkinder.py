from random import randrange
import vk_api
from vk_api import VkUpload
from vk_api.longpoll import VkLongPoll, VkEventType
from datetime import date, datetime
import requests
import sqlalchemy

def get_user_token(vkinder):
    with open('vk_user_token.txt', 'r') as file_object:
        user_token = file_object.read().strip()
    return user_token

def get_group_token(vkinder):
    with open('vk_group_token.txt', 'r') as file_object:
        group_token = file_object.read().strip()
    return group_token

class VKinder:
    def __init__(self):
        self.user_token = get_user_token(self)
        self.group_token = get_group_token(self)
        self.user_session = vk_api.VkApi(token=self.user_token)
        self.user_api = self.user_session.get_api()
        self.group_session = vk_api.VkApi(token=self.group_token)
        self.group_api = self.group_session.get_api()
        self.upload = VkUpload(self.group_session)
        self.session = requests.Session()
        self.longpool = VkLongPoll(self.group_session)

    def write_msg(self, user_id, message, attachment=None):
        self.group_api.messages.send(user_id=user_id, message=message, attachment=attachment, random_id=randrange(10 ** 7))

    def calculate_age(self, born):
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def get_url(self, id_user):
        return f'https://vk.com/id{id_user}'

    def get_city_id(self, country_id, q):
        response = self.user_api.database.getCities(country_id=country_id, q=q)
        for item in response['items']:
            if item.get('title') == q:
                return item['id']
        return None

    def get_country_id(self, country_name):
        response = self.user_api.database.getCountries(need_all=1, count=1000)
        for item in response['items']:
            if item.get('title') == country_name:
                return item['id']
        return None

    def get_info(self, user_id):
        info = {}
        info['id'] = user_id
        info['firstname'] = self.user_api.users.get(user_ids=user_id)[0]['first_name']
        info['lastname'] = self.user_api.users.get(user_ids=user_id)[0]['last_name']
        response = self.user_api.users.get(user_ids=user_id, fields=['bdate', 'sex', 'city', 'relation'])
        if response[0].get('bdate') != None:
            if len(response[0].get('bdate')) > 5:
                born = datetime.strptime(response[0]['bdate'], '%d.%m.%Y')
                age = self.calculate_age(born)
                info['age'] = age
            else:
                info['age'] = None
        else:
            info['age'] = None
        info['sex'] = response[0]['sex']
        if response[0].get('city') == None:
            info['city'] = None
        else:
            info['city'] = response[0]['city']['id']
        if response[0].get('relation') != None:
            info['relation'] = response[0]['relation']
        else:
            info['relation'] = 0
        return info

    def search_people(self, info, count=1000):
        id_list = []
        age = info['age']
        if info['sex'] == 1:
            sex = 2
        else:
            sex = 1

        if isinstance(info['city'], int):
            city = info['city']
            response = self.user_api.users.search(age_from=age - 3, age_to=age + 3, sex=sex, city=city, status=6, count=count, has_photo=1)
        else:
            info['country'] = self.get_country_id(info['country'])
            info['city'] = self.get_city_id(info['country'], info['city'])
            response = self.user_api.users.search(age_from=age - 3, age_to=age + 3, sex=sex, city=info['city'], status=6, count=count, has_photo=1)

        for item in response['items']:
            if item['is_closed'] == False:
                id_list.append(item['id'])
        return id_list

    def get_photos(self, user_id):
        likes = []
        count_comments = []
        url = []
        response = self.user_api.photos.get(owner_id=user_id, album_id='profile', extended=1, photo_sizes=1)
        items = response['items']
        for item in items:
            likes.append(item['likes']['count'])
            count_comments.append(item['comments']['count'])
            for size in item['sizes']:
                if size['type'] == 'x':
                    url.append(size['url'])
        all_photos = list(zip(likes, count_comments, url))
        all_photos.sort(reverse=True)
        url_photos = []
        for i in range(3):
            try:
                url_photos.append(all_photos[i][2])
            except IndexError:
                continue
        return url_photos

    def find_person(self, id, event_id):
        info = {}
        attachments = []
        response = self.user_api.users.get(user_ids=id, fields=['age', 'sex', 'city', 'bdate'])
        first_name = response[0]['first_name']
        last_name = response[0]['last_name']
        bdate = datetime.strptime(response[0]['bdate'], '%d.%m.%Y')
        age = self.calculate_age(bdate)
        sex = response[0]['sex']
        city = response[0]['city']['id']
        self.write_msg(event_id, f'{first_name} {last_name}')
        for url in self.get_photos(id):
            image_url = url
            image = self.session.get(image_url, stream=True)
            photo = self.upload.photo_messages(photos=image.raw)[0]
            attachments.append('photo{}_{}'.format(photo['owner_id'], photo['id']))
        self.write_msg(event_id, self.get_url(id), attachments)
        info['vk_id'] = id
        info['firstname'] = first_name
        info['lastname'] = last_name
        info['age'] = age
        info['sex'] = sex
        info['city'] = city
        return info

    def start_bot(self, db):
        while True:
            for event in self.longpool.listen():
                if event.type == VkEventType.MESSAGE_NEW:
                    if event.to_me:
                        user_id = event.text
                        self.write_msg(event.user_id, 'Идет поиск...')
                        try:
                            info = self.get_info(user_id)
                            if info['relation'] != 1 and info['relation'] != 6 and info['relation'] != 0:
                                self.write_msg(event.user_id,
                                          'У пользователя уже есть пара, введите другого пользователя ВК.')
                                continue

                            elif info['age'] == None and info['city'] != None:
                                self.write_msg(event.user_id, 'Возраст пользователя не указан, введите возраст')
                                self.write_msg(event.user_id, 'Например: возраст 18')
                                break

                            elif info['age'] != None and info['city'] == None:
                                self.write_msg(event.user_id, 'Город пользователя не указан, введите страну и город')
                                self.write_msg(event.user_id, 'Например: страна Россия город Москва')
                                break

                            elif info['age'] == None and info['city'] == None:
                                self.write_msg(event.user_id,
                                          'Возраст и город у пользователя не указан, введите возраст и город')
                                self.write_msg(event.user_id, 'Например: возраст 18 страна Россия город Москва')
                                break

                            else:
                                try:
                                    db.insert_vk_user(info)
                                except sqlalchemy.exc.IntegrityError:
                                    pass
                                id_list = self.search_people(info)
                                self.write_msg(event.user_id, f'Найдено {len(id_list)} совпадений')
                                id = id_list[0]
                                info = self.find_person(id, event.user_id)
                                try:
                                    db.insert_couple(info, user_id)
                                except sqlalchemy.exc.IntegrityError:
                                    pass
                                self.write_msg(event.user_id, 'Листать дальше? ("+" - да, "-" - нет)')
                                break
                        except vk_api.exceptions.ApiError:
                            self.write_msg(event.user_id, 'Пользователь не найден, попробуйте еще раз')
                            continue

            for event in self.longpool.listen():
                if event.type == VkEventType.MESSAGE_NEW:
                    if event.to_me:
                        text = event.text
                        if text == '+':
                            id_list.pop(0)
                            id = id_list[0]
                            info = self.find_person(id, event.user_id)
                            try:
                                db.insert_couple(info, user_id)
                            except sqlalchemy.exc.IntegrityError:
                                pass
                            self.write_msg(event.user_id, 'Листать дальше? ("+" - да, "-" - нет)')

                        elif text == '-':
                            self.write_msg(event.user_id, 'До свидания!')
                            break

                        elif 'возраст' in text and 'город' in text:
                            values = text.split(maxsplit=5)
                            if self.get_country_id(values[3]) != None:
                                info['country'] = self.get_country_id(values[3])
                            else:
                                self.write_msg(event.user_id, 'Страна не найдена, начните заново, введите пользователя: ')
                                break
                            if self.get_city_id(info['country'], values[5]) != None:
                                info['city'] = self.get_city_id(info['country'], values[5])
                            else:
                                self.write_msg(event.user_id, 'Город не найден, начните заново, введите пользователя: ')
                                break
                            info['age'] = int(values[1])
                            try:
                                db.insert_vk_user(info)
                            except sqlalchemy.exc.IntegrityError:
                                pass
                            id_list = self.search_people(info)
                            self.write_msg(event.user_id, f'Найдено {len(id_list)} совпадений')
                            id = id_list[0]
                            info = self.find_person(id, event.user_id)
                            try:
                                db.insert_couple(info, user_id)
                            except sqlalchemy.exc.IntegrityError:
                                pass
                            self.write_msg(event.user_id, 'Листать дальше? ("+" - да, "-" - нет)')
                            continue

                        elif 'возраст' in text:
                            values = text.split()
                            info['age'] = int(values[1])
                            try:
                                db.insert_vk_user(info)
                            except sqlalchemy.exc.IntegrityError:
                                pass
                            id_list = self.search_people(info)
                            self.write_msg(event.user_id, f'Найдено {len(id_list)} совпадений')
                            id = id_list[0]
                            info = self.find_person(id, event.user_id)
                            try:
                                db.insert_couple(info, user_id)
                            except sqlalchemy.exc.IntegrityError:
                                pass
                            self.write_msg(event.user_id, 'Листать дальше? ("+" - да, "-" - нет)')
                            continue

                        elif 'город' in text:
                            values = text.split(maxsplit=3)
                            if self.get_country_id(values[1]) != None:
                                info['country'] = self.get_country_id(values[1])
                            else:
                                self.write_msg(event.user_id, 'Страна не найдена, начните заново, введите пользователя: ')
                                break
                            if self.get_city_id(info['country'], values[3]) != None:
                                info['city'] = self.get_city_id(info['country'], values[3])
                            else:
                                self.write_msg(event.user_id, 'Город не найден, начните заново, введите пользователя: ')
                                break
                            try:
                                db.insert_vk_user(info)
                            except sqlalchemy.exc.IntegrityError:
                                pass
                            id_list = self.search_people(info)
                            self.write_msg(event.user_id, f'Найдено {len(id_list)} совпадений')
                            id = id_list[0]
                            info = self.find_person(id, event.user_id)
                            try:
                                db.insert_couple(info, user_id)
                            except sqlalchemy.exc.IntegrityError:
                                pass
                            self.write_msg(event.user_id, 'Листать дальше? ("+" - да, "-" - нет)')
                            continue

                        else:
                            self.write_msg(event.user_id, 'Не поняла вашего ответа...')