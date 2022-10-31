from faker import Faker
from core.models import Practice

fake = Faker()
counter = 0

LIST_OF_FAKE_PRACTICES = []

def FakerMakerPractices(Class:Practice, list,):
    fake_Pract = Practice(fake.random_int(1000, 2000), f"{fake.first_name()}'s Dential",
    industry = "Dential", active = fake.boolean(chance_of_getting_true=80))
    list.append(fake_Pract)

while counter < 5:
    FakerMakerPractices(Practice, LIST_OF_FAKE_PRACTICES)
    counter += 1

