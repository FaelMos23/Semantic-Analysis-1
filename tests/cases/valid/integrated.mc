int dobro(int x) {
    return x * 2;
}

void mostrar(bool valor) {
    print("valor = ", valor);
}

int main() {
    int x = dobro(2);
    {
        bool x = true;
        mostrar(x);
    }
    return x;
}
