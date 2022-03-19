from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("netsapiens_integration", "0016_cdrr_prefix_for_orig_callid"),
    ]

    operations = [
        migrations.RenameModel("NetsapiensCallSubscriptions", "NetsapiensCallSubscription"),
        migrations.RenameModel("NetsapiensCallSubscriptionsEventExtract", "NetsapiensCallSubscriptionEventExtract"),
        migrations.RenameModel("NetsapiensAPICredentials", "NetsapiensAPICredential"),
    ]
