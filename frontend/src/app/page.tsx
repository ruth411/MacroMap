"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { checkHealth, HealthResponse } from "@/lib/api";
import Link from "next/link";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-50 to-zinc-100 dark:from-zinc-950 dark:to-zinc-900">
      <div className="container mx-auto px-4 py-16">
        <header className="text-center mb-16">
          <h1 className="text-5xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 mb-4">
            MacroMap
          </h1>
          <p className="text-xl text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
            A grounded Financial Analyst Copilot with evidence-backed citations
            and verified computations
          </p>
        </header>

        <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto mb-12">
          <Card>
            <CardHeader>
              <CardTitle>RAG-Powered</CardTitle>
              <CardDescription>
                Retrieval over SEC filings with precise citations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Every claim is backed by evidence from 10-K, 10-Q, and 8-K filings
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Verified Computation</CardTitle>
              <CardDescription>
                Accurate financial metrics and ratios
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Margins, growth rates, and liquidity ratios computed from structured data
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Cross-Company</CardTitle>
              <CardDescription>
                Compare companies with consistent metrics
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Standardized comparisons across any companies in the index
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="text-center mb-12">
          <Link href="/chat">
            <Button size="lg" className="text-lg px-8">
              Start Analysis
            </Button>
          </Link>
        </div>

        <Card className="max-w-md mx-auto">
          <CardHeader>
            <CardTitle className="text-sm">System Status</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-sm text-zinc-500">Checking backend connection...</p>
            ) : error ? (
              <div className="text-sm">
                <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-2"></span>
                <span className="text-red-600 dark:text-red-400">
                  Backend offline: {error}
                </span>
              </div>
            ) : health ? (
              <div className="text-sm">
                <span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-2"></span>
                <span className="text-green-600 dark:text-green-400">
                  {health.app} v{health.version} - {health.status}
                </span>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
