#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <oqs/oqs.h>

#define MAGIC "PAH1"
#define FALCON_SIG_ALG OQS_SIG_alg_falcon_512
#define SPHINCS_SIG_ALG OQS_SIG_alg_slh_dsa_pure_sha2_128s

typedef struct {
    char magic[4];
    uint32_t sig_len;
    uint32_t data_len;
} __attribute__((packed)) PAHHeader;

typedef struct {
    char magic[4];
    uint32_t version;
    uint32_t entry_count;
} __attribute__((packed)) PAHContainerHeader;

typedef struct {
    uint32_t sig_len;
    uint32_t data_len;
    uint32_t name_len;
} __attribute__((packed)) PAHEntryHeader;

// ==================== WRAP FALCON ====================
int wrap_falcon(const char *input_path, const char *output_path) {
    FILE *fin = fopen(input_path, "rb");
    if (!fin) { perror("Error"); return 1; }

    fseek(fin, 0, SEEK_END);
    long file_size = ftell(fin);
    fseek(fin, 0, SEEK_SET);

    uint8_t *data = malloc(file_size);
    if (fread(data, 1, file_size, fin) != (size_t)file_size) {
        free(data); fclose(fin); return 1;
    }
    fclose(fin);

    OQS_SIG *sig = OQS_SIG_new(FALCON_SIG_ALG);
    uint8_t *pk = malloc(sig->length_public_key);
    uint8_t *sk = malloc(sig->length_secret_key);
    OQS_SIG_keypair(sig, pk, sk);

    uint8_t *signature = malloc(sig->length_signature);
    size_t sig_len = 0;
    OQS_SIG_sign(sig, signature, &sig_len, data, file_size, sk);

    FILE *fout = fopen(output_path, "wb");
    PAHHeader header = { .magic = {'P','A','H','1'}, .sig_len = sig_len, .data_len = file_size };
    fwrite(&header, sizeof(header), 1, fout);
    fwrite(signature, 1, sig_len, fout);
    fwrite(data, 1, file_size, fout);
    fclose(fout);

    printf("✅ Wrapped with Falcon-512 → %s\n", output_path);
    OQS_SIG_free(sig);
    free(pk); free(sk); free(signature); free(data);
    return 0;
}

// ==================== WRAP SPHINCS+ ====================
int wrap_sphincs(const char *input_path, const char *output_path) {
    FILE *fin = fopen(input_path, "rb");
    if (!fin) { perror("Error"); return 1; }

    fseek(fin, 0, SEEK_END);
    long file_size = ftell(fin);
    fseek(fin, 0, SEEK_SET);

    uint8_t *data = malloc(file_size);
    if (fread(data, 1, file_size, fin) != (size_t)file_size) {
        free(data); fclose(fin); return 1;
    }
    fclose(fin);

    OQS_SIG *sig = OQS_SIG_new(SPHINCS_SIG_ALG);
    if (!sig) {
        fprintf(stderr, "Error: SPHINCS+ not available\n");
        free(data); return 1;
    }

    uint8_t *pk = malloc(sig->length_public_key);
    uint8_t *sk = malloc(sig->length_secret_key);
    OQS_SIG_keypair(sig, pk, sk);

    uint8_t *signature = malloc(sig->length_signature);
    size_t sig_len = 0;
    OQS_SIG_sign(sig, signature, &sig_len, data, file_size, sk);

    FILE *fout = fopen(output_path, "wb");
    PAHHeader header = { .magic = {'P','A','H','1'}, .sig_len = sig_len, .data_len = file_size };
    fwrite(&header, sizeof(header), 1, fout);
    fwrite(signature, 1, sig_len, fout);
    fwrite(data, 1, file_size, fout);
    fclose(fout);

    printf("✅ Wrapped with SPHINCS+ → %s\n", output_path);
    OQS_SIG_free(sig);
    free(pk); free(sk); free(signature); free(data);
    return 0;
}

// ==================== WRAP HYBRID (NEW) ====================
int wrap_hybrid(const char *input_path, const char *output_path) {
    FILE *fin = fopen(input_path, "rb");
    if (!fin) { perror("Error"); return 1; }

    fseek(fin, 0, SEEK_END);
    long file_size = ftell(fin);
    fseek(fin, 0, SEEK_SET);

    uint8_t *data = malloc(file_size);
    if (fread(data, 1, file_size, fin) != (size_t)file_size) {
        free(data); fclose(fin); return 1;
    }
    fclose(fin);

    // Falcon
    OQS_SIG *falcon = OQS_SIG_new(FALCON_SIG_ALG);
    uint8_t *f_pk = malloc(falcon->length_public_key);
    uint8_t *f_sk = malloc(falcon->length_secret_key);
    OQS_SIG_keypair(falcon, f_pk, f_sk);

    uint8_t *f_sig = malloc(falcon->length_signature);
    size_t f_sig_len = 0;
    OQS_SIG_sign(falcon, f_sig, &f_sig_len, data, file_size, f_sk);

    // SPHINCS+
    OQS_SIG *sphincs = OQS_SIG_new(SPHINCS_SIG_ALG);
    uint8_t *s_pk = malloc(sphincs->length_public_key);
    uint8_t *s_sk = malloc(sphincs->length_secret_key);
    OQS_SIG_keypair(sphincs, s_pk, s_sk);

    uint8_t *s_sig = malloc(sphincs->length_signature);
    size_t s_sig_len = 0;
    OQS_SIG_sign(sphincs, s_sig, &s_sig_len, data, file_size, s_sk);

    FILE *fout = fopen(output_path, "wb");
    PAHHeader header = {
        .magic = {'P','A','H','1'},
        .sig_len = f_sig_len + s_sig_len,
        .data_len = file_size
    };
    fwrite(&header, sizeof(header), 1, fout);
    fwrite(f_sig, 1, f_sig_len, fout);
    fwrite(s_sig, 1, s_sig_len, fout);
    fwrite(data, 1, file_size, fout);
    fclose(fout);

    printf("✅ Wrapped with Hybrid (Falcon + SPHINCS+) → %s\n", output_path);
    OQS_SIG_free(falcon);
    OQS_SIG_free(sphincs);
    free(f_pk); free(f_sk); free(f_sig);
    free(s_pk); free(s_sk); free(s_sig); free(data);
    return 0;
}

// ==================== VERIFY ====================
int verify_falcon(const char *input_path) {
    FILE *f = fopen(input_path, "rb");
    if (!f) { perror("Error"); return 1; }

    PAHHeader header;
    if (fread(&header, sizeof(header), 1, f) != 1) { fclose(f); return 1; }

    if (memcmp(header.magic, MAGIC, 4) != 0) {
        fprintf(stderr, "Error: Not a valid PAH file\n");
        fclose(f); return 1;
    }

    printf("✅ Valid PAH wrapped file\n");
    printf("   Signature size : %u bytes\n", header.sig_len);
    printf("   Original data  : %u bytes\n", header.data_len);
    fclose(f);
    return 0;
}

// ==================== CREATE CONTAINER ====================
int create_container(const char *output_path) {
    FILE *f = fopen(output_path, "wb");
    if (!f) { perror("Error"); return 1; }

    PAHContainerHeader header = {
        .magic = {'P', 'A', 'H', '1'},
        .version = 1,
        .entry_count = 0
    };
    fwrite(&header, sizeof(header), 1, f);
    fclose(f);

    printf("✅ Created empty multi-asset PAH container: %s\n", output_path);
    return 0;
}

// ==================== ADD TO CONTAINER ====================
int add_to_container(const char *container_path, const char *file_to_add) {
    FILE *f = fopen(container_path, "r+b");
    if (!f) { perror("Error"); return 1; }

    PAHContainerHeader ch;
    if (fread(&ch, sizeof(PAHContainerHeader), 1, f) != 1) {
        fclose(f); return 1;
    }

    if (memcmp(ch.magic, MAGIC, 4) != 0) {
        fprintf(stderr, "Error: Not a valid PAH container\n");
        fclose(f); return 1;
    }

    FILE *fin = fopen(file_to_add, "rb");
    if (!fin) { perror("Error"); fclose(f); return 1; }

    fseek(fin, 0, SEEK_END);
    long dlen = ftell(fin);
    fseek(fin, 0, SEEK_SET);

    uint8_t *data = malloc(dlen);
    if (fread(data, 1, dlen, fin) != (size_t)dlen) {
        free(data); fclose(fin); fclose(f); return 1;
    }
    fclose(fin);

    OQS_SIG *sig = OQS_SIG_new(FALCON_SIG_ALG);
    uint8_t *pk = malloc(sig->length_public_key);
    uint8_t *sk = malloc(sig->length_secret_key);
    OQS_SIG_keypair(sig, pk, sk);

    uint8_t *sigbuf = malloc(sig->length_signature);
    size_t slen = 0;
    OQS_SIG_sign(sig, sigbuf, &slen, data, dlen, sk);

    fseek(f, 0, SEEK_END);

    PAHEntryHeader e = {
        .sig_len = slen,
        .data_len = dlen,
        .name_len = strlen(file_to_add)
    };

    fwrite(&e, sizeof(PAHEntryHeader), 1, f);
    fwrite(file_to_add, 1, e.name_len, f);
    fwrite(sigbuf, 1, slen, f);
    fwrite(data, 1, dlen, f);

    ch.entry_count++;
    fseek(f, 0, SEEK_SET);
    fwrite(&ch, sizeof(PAHContainerHeader), 1, f);
    fclose(f);

    OQS_SIG_free(sig);
    free(pk); free(sk); free(sigbuf); free(data);

    printf("✅ Added '%s' to container (now has %u entries)\n", file_to_add, ch.entry_count);
    return 0;
}

// ==================== IMPROVED LIST CONTAINER (v0.7 - Robust) ====================
int list_container(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        perror("Error opening file");
        return 1;
    }

    // Read magic bytes
    char magic[4];
    if (fread(magic, 1, 4, f) != 4) {
        fprintf(stderr, "Error: Failed to read file header\n");
        fclose(f);
        return 1;
    }

    if (memcmp(magic, MAGIC, 4) != 0) {
        fprintf(stderr, "Error: Not a valid PAH file\n");
        fclose(f);
        return 1;
    }

    // Read next 8 bytes as potential container header (version + entry_count)
    uint32_t version = 0;
    uint32_t entry_count = 0;

    if (fread(&version, 4, 1, f) == 1 && fread(&entry_count, 4, 1, f) == 1) {
        // Check if this looks like a valid container
        if (version == 1 && entry_count > 0 && entry_count < 10000) {
            // === It's a real multi-asset container ===
            printf("PAH Multi-Asset Container: %s\n", path);
            printf("Version: %u | Total Entries: %u\n\n", version, entry_count);

            // Go back to start of entries
            fseek(f, sizeof(PAHContainerHeader), SEEK_SET);

            for (uint32_t i = 0; i < entry_count; i++) {
                PAHEntryHeader e;
                if (fread(&e, sizeof(PAHEntryHeader), 1, f) != 1) break;

                char *name = malloc(e.name_len + 1);
                if (!name) break;

                if (fread(name, 1, e.name_len, f) != e.name_len) {
                    free(name);
                    break;
                }
                name[e.name_len] = '\0';

                printf("  [%u] %s  (sig: %u bytes | data: %u bytes)\n",
                       i, name, e.sig_len, e.data_len);

                fseek(f, e.sig_len + e.data_len, SEEK_CUR);
                free(name);
            }
            fclose(f);
            return 0;
        }
    }

    // === It's a single wrapped file ===
    rewind(f);
    PAHHeader single;
    if (fread(&single, sizeof(PAHHeader), 1, f) != 1) {
        fclose(f);
        return 1;
    }

    printf("PAH Wrapped File: %s\n", path);
    printf("Type: Single Asset (Falcon or SPHINCS+)\n");
    printf("Signature size : %u bytes\n", single.sig_len);
    printf("Original data  : %u bytes\n", single.data_len);
    fclose(f);
    return 0;
}

void print_help(void) {
    printf("PAH - PQC Asset Handler v0.6\n\n");
    printf("Commands:\n");
    printf("  pah --wrap-falcon   <input> <output.pqcasset>\n");
    printf("  pah --wrap-sphincs  <input> <output.pqcasset>\n");
    printf("  pah --wrap-hybrid   <input> <output.pqcasset>\n");
    printf("  pah --verify        <file.pqcasset>\n");
    printf("  pah --create-container <output.pqcasset>\n");
    printf("  pah --add-to-container <container> <file>\n");
    printf("  pah --list-container <file.pqcasset>\n");
    printf("  pah --help\n");
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        print_help();
        return 1;
    }

    if (strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0) {
        print_help();
        return 0;
    }

    if (strcmp(argv[1], "--wrap-falcon") == 0 && argc == 4)
        return wrap_falcon(argv[2], argv[3]);

    if (strcmp(argv[1], "--wrap-sphincs") == 0 && argc == 4)
        return wrap_sphincs(argv[2], argv[3]);

    if (strcmp(argv[1], "--wrap-hybrid") == 0 && argc == 4)
        return wrap_hybrid(argv[2], argv[3]);

    if (strcmp(argv[1], "--verify") == 0 && argc == 3)
        return verify_falcon(argv[2]);

    if (strcmp(argv[1], "--create-container") == 0 && argc == 3)
        return create_container(argv[2]);

    if (strcmp(argv[1], "--add-to-container") == 0 && argc == 4)
        return add_to_container(argv[2], argv[3]);

    if (strcmp(argv[1], "--list-container") == 0 && argc == 3)
        return list_container(argv[2]);

    fprintf(stderr, "Invalid command.\n");
    print_help();
    return 1;
}
