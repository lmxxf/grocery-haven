.text
 .globl proxy_0
 .def proxy_0; .scl 2; .type 32; .endef
 .seh_proc proxy_0
proxy_0:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $0, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_1
 .def proxy_1; .scl 2; .type 32; .endef
 .seh_proc proxy_1
proxy_1:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $1, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_2
 .def proxy_2; .scl 2; .type 32; .endef
 .seh_proc proxy_2
proxy_2:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $2, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_3
 .def proxy_3; .scl 2; .type 32; .endef
 .seh_proc proxy_3
proxy_3:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $3, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_4
 .def proxy_4; .scl 2; .type 32; .endef
 .seh_proc proxy_4
proxy_4:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $4, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_5
 .def proxy_5; .scl 2; .type 32; .endef
 .seh_proc proxy_5
proxy_5:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $5, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_6
 .def proxy_6; .scl 2; .type 32; .endef
 .seh_proc proxy_6
proxy_6:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $6, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_7
 .def proxy_7; .scl 2; .type 32; .endef
 .seh_proc proxy_7
proxy_7:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $7, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_8
 .def proxy_8; .scl 2; .type 32; .endef
 .seh_proc proxy_8
proxy_8:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $8, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_9
 .def proxy_9; .scl 2; .type 32; .endef
 .seh_proc proxy_9
proxy_9:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $9, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_10
 .def proxy_10; .scl 2; .type 32; .endef
 .seh_proc proxy_10
proxy_10:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $10, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_11
 .def proxy_11; .scl 2; .type 32; .endef
 .seh_proc proxy_11
proxy_11:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $11, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_12
 .def proxy_12; .scl 2; .type 32; .endef
 .seh_proc proxy_12
proxy_12:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $12, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_13
 .def proxy_13; .scl 2; .type 32; .endef
 .seh_proc proxy_13
proxy_13:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $13, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_14
 .def proxy_14; .scl 2; .type 32; .endef
 .seh_proc proxy_14
proxy_14:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $14, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_15
 .def proxy_15; .scl 2; .type 32; .endef
 .seh_proc proxy_15
proxy_15:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $15, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_16
 .def proxy_16; .scl 2; .type 32; .endef
 .seh_proc proxy_16
proxy_16:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $16, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_17
 .def proxy_17; .scl 2; .type 32; .endef
 .seh_proc proxy_17
proxy_17:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $17, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_18
 .def proxy_18; .scl 2; .type 32; .endef
 .seh_proc proxy_18
proxy_18:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $18, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
 .globl proxy_19
 .def proxy_19; .scl 2; .type 32; .endef
 .seh_proc proxy_19
proxy_19:
 subq $168, %rsp
 .seh_stackalloc 168
 .seh_endprologue
 movq %rcx, 32(%rsp)
 movq %rdx, 40(%rsp)
 movq %r8, 48(%rsp)
 movq %r9, 56(%rsp)
 movdqu %xmm0, 64(%rsp)
 movdqu %xmm1, 80(%rsp)
 movdqu %xmm2, 96(%rsp)
 movdqu %xmm3, 112(%rsp)
 movl $19, %ecx
 call resolve_export
 movq 32(%rsp), %rcx
 movq 40(%rsp), %rdx
 movq 48(%rsp), %r8
 movq 56(%rsp), %r9
 movdqu 64(%rsp), %xmm0
 movdqu 80(%rsp), %xmm1
 movdqu 96(%rsp), %xmm2
 movdqu 112(%rsp), %xmm3
 addq $168, %rsp
 jmp *%rax
 .seh_endproc
