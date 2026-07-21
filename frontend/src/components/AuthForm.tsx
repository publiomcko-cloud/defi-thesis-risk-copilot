"use client";

import { FormEvent, useState } from "react";

type AuthFormProps = {
  mode: "login" | "signup" | "forgot" | "reset";
};

const copy = {
  login: {
    title: "Log in",
    submit: "Log in",
    endpoint: "/api/auth/login",
    success: "Signed in. You can continue to your account."
  },
  signup: {
    title: "Create account",
    submit: "Sign up",
    endpoint: "/api/auth/signup",
    success: "Check your email to verify your account."
  },
  forgot: {
    title: "Recover password",
    submit: "Send recovery email",
    endpoint: "/api/auth/forgot-password",
    success: "If recovery is available for that address, instructions will be sent."
  },
  reset: {
    title: "Reset password",
    submit: "Update password",
    endpoint: "/api/auth/reset-password",
    success: "Password updated."
  }
};

export function AuthForm({ mode }: AuthFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const needsEmail = mode !== "reset";
  const needsPassword = mode !== "forgot";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("loading");
    setMessage("");
    const response = await fetch(copy[mode].endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      setStatus("error");
      setMessage("The request could not be completed. Check the fields and try again.");
      return;
    }
    setStatus("success");
    setMessage(copy[mode].success);
    if (mode === "login") {
      window.location.assign(typeof body.next === "string" ? body.next : "/account");
    }
  }

  return (
    <form className="form-panel auth-form" onSubmit={submit}>
      <h2>{copy[mode].title}</h2>
      {needsEmail ? (
        <label>
          Email
          <input
            autoComplete="email"
            inputMode="email"
            name="email"
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </label>
      ) : null}
      {needsPassword ? (
        <label>
          Password
          <input
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={8}
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
      ) : null}
      {mode === "signup" ? (
        <label className="checkbox-row">
          <input required type="checkbox" />I accept the terms and privacy policy.
        </label>
      ) : null}
      <button className="primary-action" disabled={status === "loading"} type="submit">
        {status === "loading" ? "Working..." : copy[mode].submit}
      </button>
      {message ? <p className={status === "error" ? "form-error" : "form-success"}>{message}</p> : null}
    </form>
  );
}
