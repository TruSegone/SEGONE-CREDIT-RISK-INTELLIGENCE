import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { NavLink, Route, Routes } from 'react-router-dom';
import {
  Activity,
  BarChart3,
  BrainCircuit,
  Database,
  FileQuestion,
  FlaskConical,
  Menu,
  ShieldCheck,
} from 'lucide-react';

import { exportUrl, get, post } from './api';

type PortfolioSummary = {
  applications: number;
  simulated_defaults: number;
  observed_default_rate: number;
  average_predicted_probability: number;
  high_risk_count: number;
};

type PortfolioRecord = {
  application_id: string;
  loan_purpose: string;
  loan_amount: number;
  probability_default: number;
  risk_band: string;
  defaulted: number;
};

type PredictionResponse = {
  assessment_id: string;
  model_version: string;
  probability_default: number;
  risk_band: string;
  assessed_at: string;
  explanation_available: boolean;
  disclaimer: string;
};

type ModelComparison = {
  status?: string;
  selection_rule?: string;
  models: Record<string, unknown>;
};

const navigation = [
  { path: '/', label: 'Overview', icon: Activity },
  { path: '/portfolio', label: 'Portfolio Analytics', icon: BarChart3 },
  { path: '/assess', label: 'Applicant Assessment', icon: ShieldCheck },
  { path: '/models', label: 'Model Laboratory', icon: FlaskConical },
  { path: '/explain', label: 'Explainability', icon: BrainCircuit },
  { path: '/data', label: 'Data Explorer', icon: Database },
  { path: '/about', label: 'About & Methodology', icon: FileQuestion },
];

/** Persistent navigation and the product-level responsible-use notice. */
function App() {
  const [navigationOpen, setNavigationOpen] = useState(false);

  return (
    <div className="shell">
      <aside className={navigationOpen ? 'sidebar open' : 'sidebar'}>
        <div className="brand">
          <div className="mark">S</div>
          <div>
            <b>SEGONE</b>
            <small>ENGINEERING</small>
          </div>
        </div>

        <nav aria-label="Main navigation">
          {navigation.map(({ path, label, icon: Icon }) => (
            <NavLink
              end={path === '/'}
              to={path}
              key={path}
              onClick={() => setNavigationOpen(false)}
            >
              <Icon size={17} aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          SYNTHETIC ENVIRONMENT
          <br />
          <span>● Model demonstration</span>
        </div>
      </aside>

      <main>
        <header>
          <button
            className="menu"
            aria-label="Toggle navigation"
            aria-expanded={navigationOpen}
            onClick={() => setNavigationOpen(!navigationOpen)}
          >
            <Menu aria-hidden="true" />
          </button>
          <div>
            <small>SEGONE / RISK INTELLIGENCE</small>
            <h1>Understand Risk. Explain Decisions. Engineer Confidence.</h1>
          </div>
          <span className="env">DEMO ENVIRONMENT</span>
        </header>

        <div className="notice" role="note">
          Educational portfolio demonstration using synthetic data. This is not
          a validated lending model or a recommendation to approve or reject a
          loan.
        </div>

        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/assess" element={<AssessmentPage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/explain" element={<ExplainabilityPage />} />
          <Route path="/data" element={<DataPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </main>
    </div>
  );
}

/** Shared API state for pages that load one endpoint on mount. */
function useApi<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let isCurrent = true;

    get<T>(path)
      .then((response) => {
        if (isCurrent) setData(response);
      })
      .catch((requestError: Error) => {
        if (isCurrent) setError(requestError.message);
      });

    return () => {
      isCurrent = false;
    };
  }, [path]);

  return { data, error };
}

function PageHeading({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="page-title">
      <div>
        <small>RISK WORKSPACE</small>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}

function ApiError({ message }: { message: string }) {
  return (
    <div role="alert" className="error">
      <b>Backend unavailable</b>
      <span>
        {message}. Start the API and initialize its synthetic model using the
        README instructions.
      </span>
    </div>
  );
}

function OverviewPage() {
  const summary = useApi<PortfolioSummary>('/api/v1/portfolio/summary');
  const records = useApi<{ items: PortfolioRecord[] }>(
    '/api/v1/portfolio/records?page_size=8',
  );

  const metrics = [
    ['Synthetic applications', summary.data?.applications],
    ['Simulated defaults', summary.data?.simulated_defaults],
    [
      'Observed default rate',
      summary.data
        ? `${(summary.data.observed_default_rate * 100).toFixed(1)}%`
        : undefined,
    ],
    [
      'Average predicted PD',
      summary.data
        ? `${(summary.data.average_predicted_probability * 100).toFixed(1)}%`
        : undefined,
    ],
    ['Higher risk segment', summary.data?.high_risk_count],
  ];

  return (
    <section>
      <div className="page-title">
        <div>
          <small>PORTFOLIO SNAPSHOT</small>
          <h2>Overview</h2>
          <p>
            Portfolio metrics from synthetic outcomes and the persisted
            demonstration model.
          </p>
        </div>
        <div className="badge">● API CONNECTED WHEN AVAILABLE</div>
      </div>

      {summary.error && <ApiError message={summary.error} />}

      <div className="kpis">
        {metrics.map(([label, value]) => (
          <div className="panel kpi" key={String(label)}>
            <small>{label}</small>
            <strong>{value ?? '—'}</strong>
            <span>Backend derived</span>
          </div>
        ))}
      </div>

      <div className="grid">
        <div className="panel">
          <h3>Recent synthetic applications</h3>
          <RecordsTable
            rows={records.data?.items ?? []}
            error={records.error}
          />
        </div>
        <div className="panel callout">
          <Activity aria-hidden="true" />
          <h3>Reading the metrics</h3>
          <p>
            Observed default rate is simulated defaults divided by applications
            with known outcomes. Average predicted probability is the mean
            model estimate. These measures describe different things.
          </p>
          <a href="/portfolio">Explore portfolio →</a>
        </div>
      </div>
    </section>
  );
}

function RecordsTable({
  rows,
  error,
}: {
  rows: PortfolioRecord[];
  error: string;
}) {
  if (error) return <ApiError message={error} />;
  if (rows.length === 0) {
    return (
      <div className="empty">
        No records loaded. Initialize the backend model to explore synthetic
        applications.
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {[
              'Application',
              'Purpose',
              'Loan amount',
              'Predicted PD',
              'Risk band',
              'Outcome',
            ].map((heading) => (
              <th key={heading}>{heading}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((record) => (
            <tr key={record.application_id}>
              <td>{record.application_id}</td>
              <td>{record.loan_purpose}</td>
              <td>{record.loan_amount.toLocaleString()}</td>
              <td>{(record.probability_default * 100).toFixed(1)}%</td>
              <td>
                <span className="tag">{record.risk_band}</span>
              </td>
              <td>
                {record.defaulted ? 'Simulated default' : 'No default'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PortfolioPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const endpoint = `/api/v1/portfolio/records?page=${page}&page_size=20${
    search ? `&search=${encodeURIComponent(search)}` : ''
  }`;
  const { data, error } = useApi<{
    items: PortfolioRecord[];
    total: number;
  }>(endpoint);

  return (
    <section>
      <PageHeading
        title="Portfolio Analytics"
        subtitle="Search synthetic records and inspect individual model estimates."
      />
      <div className="panel controls">
        <label>
          Application ID search
          <input
            placeholder="SG-000123"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
        </label>
        <a className="button" href={exportUrl}>
          Export synthetic CSV
        </a>
      </div>
      <div className="panel">
        <RecordsTable rows={data?.items ?? []} error={error} />
        <div className="pager">
          <span>{data?.total ?? 0} records</span>
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
          >
            Previous
          </button>
          <span>Page {page}</span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={!data || page * 20 >= data.total}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}

const syntheticExample = {
  annual_income: 720_000,
  loan_amount: 180_000,
  interest_rate: 14.5,
  loan_term_months: 36,
  employment_tenure_years: 5,
  debt_to_income: 0.31,
  existing_obligations: 98_000,
  previous_delinquencies: 0,
  credit_history_years: 8,
  loan_purpose: 'debt_consolidation',
  employment_category: 'salaried',
};

function AssessmentPage() {
  const [values, setValues] = useState({ ...syntheticExample });
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submitAssessment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      setResult(
        await post<PredictionResponse>('/api/v1/predictions', values),
      );
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function updateField(field: string, value: string | number) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function numberField(field: keyof typeof syntheticExample, label: string) {
    return (
      <label key={field}>
        {label}
        <input
          type="number"
          required
          step="any"
          value={values[field]}
          onChange={(event) => updateField(field, Number(event.target.value))}
        />
      </label>
    );
  }

  return (
    <section>
      <PageHeading
        title="Applicant Assessment"
        subtitle="Submit a synthetic applicant to the persisted model."
      />
      <div className="panel">
        <button
          className="text-button"
          onClick={() => setValues({ ...syntheticExample })}
        >
          Load synthetic example
        </button>

        <form onSubmit={submitAssessment} className="form-grid">
          {numberField('annual_income', 'Annual income')}
          {numberField('loan_amount', 'Loan amount')}
          {numberField('interest_rate', 'Interest rate (%)')}
          {numberField('loan_term_months', 'Loan term (months)')}
          {numberField('employment_tenure_years', 'Employment tenure (years)')}
          {numberField('debt_to_income', 'Debt-to-income ratio')}
          {numberField('existing_obligations', 'Existing obligations')}
          {numberField('previous_delinquencies', 'Previous delinquencies')}
          {numberField('credit_history_years', 'Credit history (years)')}
          <CategoryField
            label="Loan purpose"
            value={values.loan_purpose}
            choices={[
              'debt_consolidation',
              'home_improvement',
              'medical',
              'education',
              'vehicle',
            ]}
            onChange={(value) => updateField('loan_purpose', value)}
          />
          <CategoryField
            label="Employment category"
            value={values.employment_category}
            choices={['salaried', 'self_employed', 'contract', 'part_time']}
            onChange={(value) => updateField('employment_category', value)}
          />

          <div className="actions">
            <button className="button primary" disabled={busy}>
              {busy ? 'Assessing…' : 'Generate assessment'}
            </button>
            <button
              type="button"
              className="button"
              onClick={() => {
                setValues({ ...syntheticExample });
                setResult(null);
                setError('');
              }}
            >
              Reset
            </button>
          </div>
        </form>

        {error && <ApiError message={error} />}
        {result && <AssessmentResult result={result} />}
      </div>
    </section>
  );
}

function CategoryField({
  label,
  value,
  choices,
  onChange,
}: {
  label: string;
  value: string;
  choices: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {choices.map((choice) => (
          <option key={choice} value={choice}>
            {choice}
          </option>
        ))}
      </select>
    </label>
  );
}

function AssessmentResult({ result }: { result: PredictionResponse }) {
  return (
    <div className="result" aria-live="polite">
      <small>MODEL GENERATED ESTIMATE · {result.model_version}</small>
      <strong>{(result.probability_default * 100).toFixed(2)}%</strong>
      <span>{result.risk_band}</span>
      <p>{result.disclaimer}</p>
      <p>
        Local feature explanation unavailable in this build; no explanation has
        been fabricated.
      </p>
    </div>
  );
}

function ModelsPage() {
  const { data, error } = useApi<ModelComparison>('/api/v1/models/compare');

  return (
    <section>
      <PageHeading
        title="Model Laboratory"
        subtitle="Persisted validation comparison and final held-out evaluation."
      />
      {error && <ApiError message={error} />}
      <div className="panel">
        <h3>Candidate evaluation</h3>
        {data?.status === 'untrained' ? (
          <p>Train the model to populate comparison results.</p>
        ) : (
          <>
            <p>Selection rule: {data?.selection_rule}</p>
            <pre>{JSON.stringify(data?.models, null, 2)}</pre>
          </>
        )}
      </div>
    </section>
  );
}

function ExplainabilityPage() {
  return (
    <section>
      <PageHeading
        title="Explainability"
        subtitle="Interpret model behavior with appropriate limits."
      />
      <div className="panel">
        <BrainCircuit aria-hidden="true" />
        <h3>Explanation status</h3>
        <p>
          Local SHAP explanation has not been implemented. The assessment API
          explicitly reports explanation unavailable instead of inventing
          feature contributions. SHAP attribution describes model behavior, not
          causal effects.
        </p>
      </div>
    </section>
  );
}

type DataProfile = {
  rows: number;
  columns: number;
  features: Array<{
    name: string;
    dtype: string;
    missing_pct: number;
    unique: number;
  }>;
};

function DataPage() {
  const { data, error } = useApi<DataProfile>('/api/v1/data/profile');

  return (
    <section>
      <PageHeading
        title="Data Explorer"
        subtitle="Inspect schema and quality of the synthetic training set."
      />
      {error && <ApiError message={error} />}
      <div className="panel">
        <h3>
          {data
            ? `${data.rows.toLocaleString()} rows · ${data.columns} columns`
            : 'Dataset profile'}
        </h3>
        {data ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Type</th>
                  <th>Missing</th>
                  <th>Unique</th>
                </tr>
              </thead>
              <tbody>
                {data.features.map((feature) => (
                  <tr key={feature.name}>
                    <td>{feature.name}</td>
                    <td>{feature.dtype}</td>
                    <td>{feature.missing_pct}%</td>
                    <td>{feature.unique}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>Connect the backend to inspect data.</p>
        )}
      </div>
    </section>
  );
}

function AboutPage() {
  return (
    <section>
      <PageHeading
        title="About & Methodology"
        subtitle="Purpose, assumptions and responsible use."
      />
      <div className="panel prose">
        <h3>Purpose</h3>
        <p>
          SEGONE demonstrates synthetic credit-risk analysis and model inference
          for educational portfolio review.
        </p>
        <h3>Data and target</h3>
        <p>
          The reproducible generator creates synthetic applications with
          stochastic outcomes and a latent risk relationship.{' '}
          <code>defaulted=1</code> represents a simulated default outcome. IDs
          and cohort are excluded from model features.
        </p>
        <h3>Training</h3>
        <p>
          Numerical values are median-imputed and standardized; categories are
          mode-imputed and one-hot encoded. Candidate models are selected by
          validation ROC-AUC. The test split is held out until final evaluation.
          Probabilities are not calibrated to a real lending population.
        </p>
        <h3>Limitations and responsible use</h3>
        <p>
          Synthetic distributions need not represent real populations or
          lending outcomes. No independent fairness review, calibration,
          governance, regulatory review or lending validation has been
          performed. Do not use for actual credit decisions. Human oversight and
          appropriate data minimization are essential.
        </p>
        <h3>Illustrative risk bands</h3>
        <p>
          &lt;10%, 10–25%, 25–50%, and ≥50%. These are demonstration labels, not
          policy cutoffs.
        </p>
      </div>
    </section>
  );
}

export default App;
