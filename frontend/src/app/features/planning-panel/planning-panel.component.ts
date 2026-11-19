import { Component, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { PlanResponse, PlanStep } from '../../core/models/api.models';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-planning-panel',

  standalone: true,

  imports: [CommonModule, FormsModule],

  templateUrl: './planning-panel.component.html',

  styleUrl: './planning-panel.component.scss',
})
export class PlanningPanelComponent implements OnDestroy {
  readonly userId = 'demo-user';

  readonly stages = [
    'Decompose the task into steps',
    'Retrieve evidence for every step',
    'Draft the deliverable',
    'Verify claims against the evidence',
    'Wait for human approval',
  ];

  task = '';

  note = '';

  maxRevisions = 1;

  readonly result = signal<PlanResponse | null>(null);

  readonly loading = signal(false);

  readonly resuming = signal(false);

  readonly error = signal<string | null>(null);

  readonly activeStage = signal(-1);

  private timer: ReturnType<typeof setInterval> | null = null;

  constructor(private readonly api: ApiService) {}

  ngOnDestroy(): void {
    this.stopTimer();
  }

  run(): void {
    const task = this.task.trim();

    if (task.length < 5 || this.loading()) {
      return;
    }

    this.loading.set(true);
    this.error.set(null);
    this.result.set(null);
    this.note = '';
    this.activeStage.set(0);

    this.startTimer();

    this.api
      .planTask({
        task,
        user_id: this.userId,
        max_revisions: this.maxRevisions,
        limit: 5,
      })
      .subscribe({
        next: (response) => {
          this.stopTimer();
          this.result.set(response);
          this.activeStage.set(this.stageFor(response));
          this.loading.set(false);
        },

        error: () => {
          this.stopTimer();
          this.activeStage.set(-1);
          this.error.set(
            'The planning run failed. Check that the API and the language model are available.',
          );
          this.loading.set(false);
        },
      });
  }

  decide(approved: boolean): void {
    const current = this.result();

    if (!current || this.resuming()) {
      return;
    }

    this.resuming.set(true);
    this.error.set(null);

    this.api
      .resumePlan({
        thread_id: current.thread_id,
        approved,
        note: this.note.trim() || undefined,
      })
      .subscribe({
        next: (response) => {
          this.result.set(response);
          this.activeStage.set(this.stageFor(response));
          this.resuming.set(false);
        },

        error: () => {
          this.error.set('Could not resume the planning run.');
          this.resuming.set(false);
        },
      });
  }

  reset(): void {
    this.stopTimer();
    this.result.set(null);
    this.activeStage.set(-1);
    this.error.set(null);
    this.note = '';
  }

  stepIcon(step: PlanStep): string {
    if (step.status === 'completed') {
      return '✓';
    }

    if (step.status === 'empty') {
      return '∅';
    }

    return '·';
  }

  confidence(value: number | null): string {
    if (value === null || value === undefined) {
      return '—';
    }

    return `${Math.round(value * 100)}%`;
  }

  private stageFor(response: PlanResponse): number {
    if (response.status === 'interrupted') {
      return 4;
    }

    return this.stages.length;
  }

  private startTimer(): void {
    this.stopTimer();

    this.timer = setInterval(() => {
      this.activeStage.update((stage) =>
        Math.min(stage + 1, this.stages.length - 2),
      );
    }, 3200);
  }

  private stopTimer(): void {
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}
