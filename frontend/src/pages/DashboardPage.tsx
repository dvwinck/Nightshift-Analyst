import { useCallback, useEffect, useMemo, useState } from "react";

import { createCase, getCases } from "../api/cases";
import Layout from "../components/Layout";
import CaseCard from "../components/CaseCard";
import CaseForm from "../components/CaseForm";
import { useAuth } from "../hooks/useAuth";
import { Case, CaseCreatePayload } from "../types";

const DashboardPage = () => {
  const { token, user } = useAuth();

  const [cases, setCases] = useState<Case[]>([]);
  const [isFetching, setIsFetching] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sortedCases = useMemo(
    () =>
      [...cases].sort((a, b) => {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }),
    [cases]
  );

  const loadCases = useCallback(async () => {
    if (!token) {
      return;
    }

    setIsFetching(true);
    setError(null);
    try {
      const data = await getCases(token);
      setCases(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cases");
    } finally {
      setIsFetching(false);
    }
  }, [token]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  const handleCreate = useCallback(
    async (payload: CaseCreatePayload) => {
      if (!token) {
        throw new Error("Missing authentication token");
      }
      setIsCreating(true);
      setError(null);
      try {
        const created = await createCase(token, payload);
        setCases((previous) => [created, ...previous]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create case");
        throw err;
      } finally {
        setIsCreating(false);
      }
    },
    [token]
  );

  return (
    <Layout
      title="Case Files"
      actions={
        <button
          type="button"
          className="button button-secondary"
          onClick={loadCases}
          disabled={isFetching}
        >
          {isFetching ? "Refreshing..." : "Refresh"}
        </button>
      }
    >
      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {user && (
        <CaseForm userId={user.id} onCreate={handleCreate} isSubmitting={isCreating} />
      )}

      <section className="cases-section">
        <header className="section-header">
          <h2>Active Cases</h2>
          <span>{sortedCases.length}</span>
        </header>

        {isFetching && sortedCases.length === 0 && <p>Loading cases...</p>}

        {!isFetching && sortedCases.length === 0 && (
          <p className="empty-state">
            No cases yet. Create one to start charting the investigation tree.
          </p>
        )}

        <div className="card-grid">
          {sortedCases.map((caseFile) => (
            <CaseCard key={caseFile.id} caseData={caseFile} />
          ))}
        </div>
      </section>
    </Layout>
  );
};

export default DashboardPage;
