import * as Sentry from "@sentry/nextjs";

// Only initialize if DSN is set
if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "production",

    // Performance monitoring: capture 10% of transactions
    tracesSampleRate: 0.1,

    // Session replay: capture 1% of sessions, 100% of sessions with errors
    replaysSessionSampleRate: 0.01,
    replaysOnErrorSampleRate: 1.0,

    // Don't send PII
    sendDefaultPii: false,
  });
}
