#include <string>

struct User {
    bool active = true;
    bool isActive() const { return active; }
};

User* getUser(int id) {
    if (id < 0) return nullptr;
    return new User{};
}

bool authenticate(int id) {
    User* user = getUser(id);
    if (user->isActive()) {
        return true;
    }
    return false;
}

int main() {
    return authenticate(1) ? 0 : 1;
}
