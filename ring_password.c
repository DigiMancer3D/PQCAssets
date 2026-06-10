#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <getopt.h>
#include <oqs/oqs.h>
#include <openssl/evp.h>

void print_usage() {
    printf("Usage: ./ring_password \"your password here\" [options]\n");
    printf("Options:\n");
    printf("  -o, --output <file>   Write output to specified file\n");
    printf("  -h, --help            Show this help message\n");
}

int main(int argc, char *argv[]) {
    char *password = NULL;
    char *output_file = NULL;

    int opt;
    static struct option long_options[] = {
        {"output", required_argument, 0, 'o'},
        {"help",   no_argument,       0, 'h'},
        {0, 0, 0, 0}
    };

    while ((opt = getopt_long(argc, argv, "o:h", long_options, NULL)) != -1) {
        switch (opt) {
            case 'o':
                output_file = optarg;
                break;
            case 'h':
                print_usage();
                return 0;
            default:
                print_usage();
                return 1;
        }
    }

    if (optind < argc) {
        password = argv[optind];
    } else {
        fprintf(stderr, "Error: Password is required\n");
        print_usage();
        return 1;
    }

    // SHA3-512 hash (Ring0)
    unsigned char hash[64];
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    EVP_DigestInit_ex(ctx, EVP_sha3_512(), NULL);
    EVP_DigestUpdate(ctx, password, strlen(password));
    EVP_DigestFinal_ex(ctx, hash, NULL);
    EVP_MD_CTX_free(ctx);

    // Generate filename
    char filename[32];
    snprintf(filename, sizeof(filename), "%c%c%c%c%c%c.ssp",
             hash[0]%26+'a', hash[1]%26+'a', hash[2]%26+'a',
             hash[61]%26+'a', hash[62]%26+'a', hash[63]%26+'a');

    FILE *f;
    if (output_file) {
        f = fopen(output_file, "w");
    } else {
        f = fopen(filename, "w");
    }

    if (!f) {
        perror("Failed to open output file");
        return 1;
    }

    fprintf(f, "%s\n\n", filename);
    for (int i = 0; i < 64; i++) fprintf(f, "%02x", hash[i]);
    fprintf(f, "\n\nSuper Secret Password\n");
    fclose(f);

    printf("✅ Created: %s\n", output_file ? output_file : filename);
    printf("Ring0 (password hash): ");
    for (int i = 0; i < 64; i++) printf("%02x", hash[i]);
    printf("\n");

    return 0;
}
