import ldap3
class UserManager:
    """
    Sample class to manage edir users via ldap3.
    """


    def _check_password_strength(self, password):
        """
        Passwords must contain at least one lowercase, one uppercase, one special char or number, and at least 7 chars.
        """

        regexp = re.compile(r"(?=.*[a-z])(?=.*[A-Z])(?=.*[?!@#§+\-$%&*{}()]|(?=.*\d)).{7,}")
        return re.match(regexp, password) is None

    def _generate_password(self):
        """
        Passwords must contain at least one lowercase, one uppercase, one special char or number, and at least 7 chars.
        """

        charlist = string.ascii_letters + string.digits + "?!@#§+-$%&*{}()]["
        password_check = False
        while not password_check:
            password = ''.join(random.choices(charlist, k=8))
            password_check = self._check_password_strength(password)

        return password

    def set_password(self, username, password):
        try:
            self.samdb.setpassword(f"samaccountname={username}", password)
        except LdbError as e:
            logger.error(e.args[1])
            raise Exception(e.args[1])
