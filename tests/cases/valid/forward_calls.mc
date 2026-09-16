int primeiro(int n) {
    if (n == 0) {
        return 0;
    }
    return segundo(n - 1);
}

int segundo(int n) {
    return primeiro(n);
}

int main() {
    return primeiro(2);
}
