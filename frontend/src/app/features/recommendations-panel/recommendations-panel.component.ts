import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

import {
  RecommendationItem,
  RecommendationResponse,
} from '../../core/models/api.models';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-recommendations-panel',

  standalone: true,

  imports: [CommonModule],

  templateUrl: './recommendations-panel.component.html',

  styleUrl: './recommendations-panel.component.scss',
})
export class RecommendationsPanelComponent implements OnInit {
  readonly userId = 'demo-user';

  readonly recommendations = signal<RecommendationResponse | null>(null);

  readonly loading = signal(false);

  readonly error = signal<string | null>(null);

  readonly feedback = signal<Record<number, 'up' | 'down'>>({});

  constructor(private readonly api: ApiService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.loading.set(true);
    this.error.set(null);

    this.api.getRecommendations(this.userId, 5).subscribe({
      next: (response) => {
        this.recommendations.set(response);
        this.loading.set(false);
      },

      error: () => {
        this.error.set('Could not load recommendations.');
        this.loading.set(false);
      },
    });
  }

  rate(item: RecommendationItem, relevant: boolean): void {
    this.feedback.update((state) => ({
      ...state,
      [item.document_id]: relevant ? 'up' : 'down',
    }));

    this.api
      .submitRecommendationFeedback({
        user_id: this.userId,
        document_id: item.document_id,
        relevant,
      })
      .subscribe({
        next: () => this.refresh(),

        error: () => {
          this.feedback.update((state) => {
            const next = { ...state };
            delete next[item.document_id];
            return next;
          });
        },
      });
  }

  percentage(value: number): string {
    return `${Math.round(value * 100)}%`;
  }

  scoreWidth(value: number): string {
    return `${Math.max(4, Math.min(100, Math.round(value * 100)))}%`;
  }

  hasFeedback(documentId: number): 'up' | 'down' | null {
    return this.feedback()[documentId] ?? null;
  }
}
