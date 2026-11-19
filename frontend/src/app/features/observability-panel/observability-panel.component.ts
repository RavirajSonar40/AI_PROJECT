import { Component, OnInit, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

import {
  EvaluationDataset,
  EvaluationPipelineSummary,
  EvaluationRun,
  EvaluationRunDetail,
  ObservabilityOverview,
} from '../../core/models/api.models';
import { ApiService } from '../../core/services/api.service';

interface MetricRow {
  key: string;
  label: string;
  kind: 'percent' | 'number';
}

@Component({
  selector: 'app-observability-panel',

  standalone: true,

  imports: [CommonModule, FormsModule, DatePipe],

  templateUrl: './observability-panel.component.html',

  styleUrl: './observability-panel.component.scss',
})
export class ObservabilityPanelComponent implements OnInit {
  readonly metricRows: MetricRow[] = [
    {
      key: 'faithfulness',
      label: 'Faithfulness',
      kind: 'percent',
    },
    {
      key: 'answer_relevance',
      label: 'Answer relevance',
      kind: 'percent',
    },
    {
      key: 'context_precision',
      label: 'Context precision',
      kind: 'percent',
    },
    {
      key: 'context_recall',
      label: 'Context recall',
      kind: 'percent',
    },
    {
      key: 'pass_rate',
      label: 'Pass rate',
      kind: 'percent',
    },
    {
      key: 'composite_score',
      label: 'Composite score',
      kind: 'percent',
    },
    {
      key: 'avg_latency_ms',
      label: 'Avg latency',
      kind: 'number',
    },
    {
      key: 'total_tokens',
      label: 'Tokens',
      kind: 'number',
    },
  ];

  readonly overview = signal<ObservabilityOverview | null>(null);

  readonly datasets = signal<EvaluationDataset[]>([]);

  readonly runs = signal<EvaluationRun[]>([]);

  readonly selectedRun = signal<EvaluationRunDetail | null>(null);

  readonly loading = signal(false);

  readonly loadingRun = signal(false);

  readonly evaluating = signal(false);

  readonly error = signal<string | null>(null);

  hours = 24;

  dataset = 'demo_dataset';

  maxCases = 4;

  constructor(private readonly api: ApiService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading.set(true);
    this.error.set(null);

    this.api.getObservabilityOverview(this.hours).subscribe({
      next: (overview) => {
        this.overview.set(overview);
        this.loading.set(false);
      },

      error: () => {
        this.error.set('Could not load observability data.');
        this.loading.set(false);
      },
    });

    this.api.listEvaluationDatasets().subscribe({
      next: (datasets) => {
        this.datasets.set(datasets);

        if (
          datasets.length &&
          !datasets.some((item) => item.name === this.dataset)
        ) {
          this.dataset = datasets[0].name;
        }
      },
    });

    this.api.listEvaluationRuns(8).subscribe({
      next: (runs) => {
        this.runs.set(runs);

        if (!this.selectedRun() && runs.length) {
          this.openRun(runs[0].id);
        }
      },
    });
  }

  runEvaluation(): void {
    if (this.evaluating()) {
      return;
    }

    this.evaluating.set(true);
    this.error.set(null);

    this.api.runEvaluation(this.dataset, this.maxCases).subscribe({
      next: (response) => {
        this.evaluating.set(false);

        this.api.listEvaluationRuns(8).subscribe({
          next: (runs) => this.runs.set(runs),
        });

        this.openRun(response.run_id);
        this.refreshOverview();
      },

      error: () => {
        this.evaluating.set(false);
        this.error.set(
          'The evaluation run failed. Check the API logs for details.',
        );
      },
    });
  }

  openRun(runId: number): void {
    this.loadingRun.set(true);

    this.api.getEvaluationRun(runId).subscribe({
      next: (detail) => {
        this.selectedRun.set(detail);
        this.loadingRun.set(false);
      },

      error: () => {
        this.loadingRun.set(false);
      },
    });
  }

  closeRun(): void {
    this.selectedRun.set(null);
  }

  percent(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return '—';
    }

    return `${(value * 100).toFixed(1)}%`;
  }

  deltaPercent(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return '—';
    }

    const sign = value >= 0 ? '+' : '';

    return `${sign}${(value * 100).toFixed(1)}`;
  }

  deltaClass(value: number | null | undefined): string {
    if (value === null || value === undefined) {
      return '';
    }

    if (value > 0) {
      return 'up';
    }

    if (value < 0) {
      return 'down';
    }

    return '';
  }

  metricValue(
    summary: EvaluationPipelineSummary,
    row: MetricRow,
  ): string {
    const value = (
      summary as unknown as Record<string, unknown>
    )[row.key];

    if (typeof value !== 'number') {
      return '—';
    }

    if (row.kind === 'percent') {
      return this.percent(value);
    }

    return new Intl.NumberFormat('en-US').format(value);
  }

  caseMetric(
    metrics: Record<string, boolean | number | null> | null,
    key: string,
  ): string {
    const value = metrics?.[key];

    if (typeof value !== 'number') {
      return '—';
    }

    return this.percent(value);
  }

  private refreshOverview(): void {
    this.api.getObservabilityOverview(this.hours).subscribe({
      next: (overview) => this.overview.set(overview),
    });
  }
}
