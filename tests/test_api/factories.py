from faker import Faker

fake = Faker()
counter = 0
class FakePractice:
    def __init__(self,id, name, industry, active):
        self.id = id
        self.name = name
        self.industry = industry
        self.active = active

LIST_OF_FAKE_PRACTICES = []

def FakerMakerPractices(Class:FakePractice, list,):
    fake_Pract = FakePractice(fake.random_int(1000, 2000), f"{fake.first_name()}'s Dential",
    industry = "Dential", active = fake.boolean(chance_of_getting_true=80))
    list.append(fake_Pract)

while counter < 5:
    FakerMakerPractices(FakePractice, LIST_OF_FAKE_PRACTICES)
    counter += 1

