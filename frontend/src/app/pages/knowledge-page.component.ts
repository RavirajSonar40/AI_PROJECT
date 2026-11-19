import { Component } from '@angular/core';
import { DocumentPanelComponent } from '../features/document-panel/document-panel.component';
import { RecommendationsPanelComponent } from '../features/recommendations-panel/recommendations-panel.component';
import { PlanningPanelComponent } from '../features/planning-panel/planning-panel.component';

@Component({
  standalone: true,
  imports: [DocumentPanelComponent, RecommendationsPanelComponent, PlanningPanelComponent],
  template: `
    <div class="knowledge-layout">
      <app-document-panel />
      <app-recommendations-panel />
      <app-planning-panel />
    </div>
  `,
})
export class KnowledgePageComponent {}
