MESSAGE_PRIORITIES_DEFAULT = "default"
MESSAGE_PRIORITIES_HIGH = "high"

MESSAGE_STATUSES_ACCEPTED = "accepted"
MESSAGE_STATUSES_DELIVERED = "delivered"
MESSAGE_STATUSES_FAILED = "failed"
MESSAGE_STATUSES_QUEUED = "queued"
MESSAGE_STATUSES_RECEIVED = "received"
MESSAGE_STATUSES_SENDING = "sending"
MESSAGE_STATUSES_SENT = "sent"
MESSAGE_STATUSES_UNDELIVERED = "undelivered"

MESSAGE_STATUSES = [
    (MESSAGE_STATUSES_ACCEPTED, "Accepted"),
    (MESSAGE_STATUSES_DELIVERED, "Delivered"),
    (MESSAGE_STATUSES_FAILED, "Failed"),
    (MESSAGE_STATUSES_QUEUED, "Queued"),
    (MESSAGE_STATUSES_RECEIVED, "Received"),
    (MESSAGE_STATUSES_SENDING, "Sending"),
    (MESSAGE_STATUSES_SENT, "Sent"),
    (MESSAGE_STATUSES_UNDELIVERED, "Undelivered"),
]

MESSAGE_PRIORITIES = [(MESSAGE_PRIORITIES_DEFAULT, "Default"), (MESSAGE_PRIORITIES_HIGH, "High")]