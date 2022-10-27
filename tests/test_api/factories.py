import factory


class CallModelFactory(factory.DjangoModelFactory):
    class Meta:
        model = ""

    field1 = factory.faker.Faker("Phone_number")
