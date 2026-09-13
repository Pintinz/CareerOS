import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../../core/design/design.dart";
import "../../../core/widgets/widgets.dart";
import "auth_controller.dart";
import "auth_layout.dart";

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    await ref.read(authControllerProvider.notifier).register(
          email: _emailController.text.trim(),
          password: _passwordController.text,
        );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final isLoading = authState.isLoading;
    final errorMessage = ref.read(authControllerProvider.notifier).errorMessage;

    return AuthLayout(
      showBack: true,
      title: "Create your account",
      subtitle: "Start tracking jobs, scholarships and your career progress.",
      form: Form(
        key: _formKey,
        child: AutofillGroup(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.email],
                decoration: const InputDecoration(labelText: "Email", prefixIcon: Icon(Icons.alternate_email_rounded)),
                validator: (value) {
                  if (value == null || !value.contains("@")) return "Enter a valid email";
                  return null;
                },
              ),
              Gap.md,
              TextFormField(
                controller: _passwordController,
                obscureText: _obscurePassword,
                textInputAction: TextInputAction.done,
                autofillHints: const [AutofillHints.newPassword],
                onFieldSubmitted: (_) => isLoading ? null : _submit(),
                decoration: InputDecoration(
                  labelText: "Password",
                  helperText: "At least 8 characters",
                  prefixIcon: const Icon(Icons.lock_outline_rounded),
                  suffixIcon: IconButton(
                    tooltip: _obscurePassword ? "Show password" : "Hide password",
                    icon: Icon(_obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined),
                    onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                  ),
                ),
                validator: (value) {
                  if (value == null || value.length < 8) {
                    return "Password must be at least 8 characters";
                  }
                  return null;
                },
              ),
              if (errorMessage != null) ...[
                Gap.md,
                AuthErrorBanner(message: errorMessage),
              ],
              Gap.xl,
              PrimaryButton(label: "Sign Up", isLoading: isLoading, onPressed: _submit),
            ],
          ),
        ),
      ),
      footer: AuthSwitchPrompt(
        prompt: "Already have an account?",
        actionLabel: "Log in",
        onPressed: isLoading ? null : () => context.pop(),
      ),
    );
  }
}
