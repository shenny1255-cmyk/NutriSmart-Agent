"""Chặn email tạm thời/dùng một lần khi đăng ký để giảm tài khoản rác.

Danh sách giữ ở mức các nhà cung cấp phổ biến; tên miền con (vd: abc.mailinator.com) cũng bị chặn.
"""

DISPOSABLE_DOMAINS: frozenset[str] = frozenset({
    "tempmail.com", "temp-mail.org", "temp-mail.io", "tempmail.net", "tempmail.dev", "tempmailo.com",
    "tempail.com", "tempr.email", "tmpmail.org", "tmpmail.net", "tmails.net",
    "10minutemail.com", "10minutemail.net", "10minemail.com", "20minutemail.com",
    "mailinator.com", "mailinator.net", "mailinator2.com",
    "guerrillamail.com", "guerrillamail.net", "guerrillamail.org", "guerrillamail.biz",
    "guerrillamail.de", "guerrillamailblock.com", "grr.la", "pokemail.net", "spam4.me",
    "sharklasers.com",
    "yopmail.com", "yopmail.net", "yopmail.fr",
    "trashmail.com", "trashmail.net", "trashmail.de", "trash-mail.com",
    "getairmail.com", "dispostable.com", "maildrop.cc", "mailnesia.com", "mintemail.com",
    "throwawaymail.com", "fakeinbox.com", "fakemail.net", "emailondeck.com",
    "getnada.com", "nada.email", "mohmal.com", "moakt.com", "mailcatch.com",
    "mytemp.email", "burnermail.io", "spamgourmet.com", "mailpoof.com",
    "dropmail.me", "emailfake.com", "inboxkitten.com", "1secmail.com", "1secmail.net",
    "harakirimail.com", "discard.email", "spambox.us", "33mail.com",
})


def email_domain(email: str) -> str:
    return str(email).strip().lower().rsplit("@", 1)[-1]


def is_disposable_email(email: str) -> bool:
    """True nếu tên miền (hoặc tên miền cha) nằm trong danh sách email dùng một lần."""
    domain = email_domain(email)
    parts = domain.split(".")
    return any(".".join(parts[i:]) in DISPOSABLE_DOMAINS for i in range(len(parts) - 1))
