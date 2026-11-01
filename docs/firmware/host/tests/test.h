/* Mini-marco de pruebas sin dependencias. */
#ifndef OCX_TEST_H
#define OCX_TEST_H
#include <stdio.h>
#include <string.h>

static int g_fail, g_checks;

#define CHECK(c) do { g_checks++; if (!(c)) { g_fail++; \
    printf("  FALLO %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)
#define CHECK_EQ(a, b) do { long long _a = (long long)(a), _b = (long long)(b); g_checks++; \
    if (_a != _b) { g_fail++; printf("  FALLO %s:%d: %s == %s (%lld != %lld)\n", \
    __FILE__, __LINE__, #a, #b, _a, _b); } } while (0)
#define CHECK_STR_HAS(s, sub) do { g_checks++; if (!strstr((s), (sub))) { g_fail++; \
    printf("  FALLO %s:%d: \"%s\" no contiene \"%s\"\n", __FILE__, __LINE__, (s), (sub)); } } while (0)
#define RUN(fn) do { int _f = g_fail; fn(); printf("%s %s\n", g_fail == _f ? "[ ok ]" : "[FAIL]", #fn); } while (0)
#define DONE() (printf("%d comprobaciones, %d fallos\n", g_checks, g_fail), g_fail ? 1 : 0)
#endif
