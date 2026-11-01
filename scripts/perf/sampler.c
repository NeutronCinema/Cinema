/* LD_PRELOAD SIGPROF self-sampler (the 附3 method, rebuilt).
 * Samples the process PC at 200 Hz via ITIMER_PROF; writes raw hex PCs to
 * $SAMPLER_OUT (fd opened at ctor) async-signal-safely via write(2).
 * Dumps /proc/self/maps at destruct time (libs load after the ctor).
 * Build: gcc -shared -fPIC -o sampler.so sampler.c
 * Use:   LD_PRELOAD=./sampler.so SAMPLER_OUT=/tmp/pc.txt <cmd>
 */
#define _GNU_SOURCE
#include <signal.h>
#include <sys/time.h>
#include <sys/uio.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <ucontext.h>
#include <stdint.h>

static int g_fd = -1;
static volatile uint64_t g_count = 0;

static void handler(int sig, siginfo_t *si, void *uc)
{
    (void)sig; (void)si;
    if (g_fd < 0) return;
    ucontext_t *u = (ucontext_t *)uc;
    /* x86_64: RIP at gregs[REG_RIP] (16) */
    uint64_t pc = (uint64_t)u->uc_mcontext.gregs[16];
    char buf[32];
    int n = 0;
    buf[n++] = '0'; buf[n++] = 'x';
    for (int i = 15; i >= 0; --i) {
        int d = (pc >> (i * 4)) & 0xF;
        buf[n++] = d < 10 ? '0' + d : 'a' + d - 10;
    }
    buf[n++] = '\n';
    if (g_count & 1) return; /* write every other sample: cheap throttle */
    g_count++;
    write(g_fd, buf, n);
    g_count++;
}

static void dump_maps(void)
{
    char path[64];
    snprintf(path, sizeof path, "/proc/self/maps");
    int in = open(path, O_RDONLY);
    if (in < 0) return;
    char buf[4096];
    ssize_t n;
    while ((n = read(in, buf, sizeof buf)) > 0)
        write(g_fd, buf, n);
    close(in);
    char tail[] = "\n=== MAPS END ===\n";
    write(g_fd, tail, sizeof tail - 1);
}

__attribute__((constructor)) static void ctor(void)
{
    const char *out = getenv("SAMPLER_OUT");
    if (!out) return;
    g_fd = open(out, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (g_fd < 0) return;
    struct sigaction sa;
    sa.sa_sigaction = handler;
    sa.sa_flags = SA_SIGINFO | SA_RESTART;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGPROF, &sa, NULL);
    struct sigaction old;
    sigaction(SIGPROF, NULL, &old);
    struct itimerval it = {{0, 5000}, {0, 5000}}; /* 200 Hz */
    if (setitimer(ITIMER_PROF, &it, NULL) != 0) {
        char e[] = "SAMPLER: setitimer FAILED\n";
        write(2, e, sizeof e - 1);
    } else {
        char o[] = "SAMPLER: itimer armed\n";
        write(2, o, sizeof o - 1);
        struct itimerval chk;
        getitimer(ITIMER_PROF, &chk);
        char b[128];
        int n = snprintf(b, sizeof b, "SAMPLER: timer value %ld.%ld\n",
                         (long)chk.it_value.tv_sec, (long)chk.it_value.tv_usec);
        write(2, b, n);
    }
}

__attribute__((destructor)) static void dtor(void)
{
    if (g_fd < 0) return;
    struct itimerval it = {{0, 0}, {0, 0}};
    setitimer(ITIMER_PROF, &it, NULL);
    dump_maps();
    close(g_fd);
    g_fd = -1;
}
