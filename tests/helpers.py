def register(
    client,
    username="stu1",
    password="pass123",
    real_name="张三",
    role="student",
    teacher_code="",
    major="人工智能",
    grade="2024",
):
    return client.post(
        "/register",
        data={
            "username": username,
            "password": password,
            "real_name": real_name,
            "role": role,
            "teacher_code": teacher_code,
            "major": major,
            "grade": grade,
        },
        follow_redirects=False,
    )


def login(client, username="stu1", password="pass123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def make_student(client, username="stu1", real_name="张三"):
    return register(client, username=username, real_name=real_name)


def make_teacher(client, username="teacher1", real_name="李老师"):
    return register(
        client,
        username=username,
        real_name=real_name,
        role="teacher",
        teacher_code="teacher-secret",
        major="",
        grade="",
    )


def make_alumni(client, username="alumni1", real_name="王校友"):
    return register(
        client,
        username=username,
        real_name=real_name,
        role="alumni",
        major="",
        grade="",
    )
