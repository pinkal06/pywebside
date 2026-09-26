from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import constant_time_compare


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return str(user.pk) + str(timestamp) + str(user.profile.is_email_verified) + str(user.email)


email_verification_token = EmailVerificationTokenGenerator()


def is_valid_password_reset_token(user, token):
    return PasswordResetTokenGenerator().check_token(user, token)


def verify_email_token(user, token):
    return email_verification_token.check_token(user, token)
