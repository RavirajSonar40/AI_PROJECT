import { Component } from '@angular/core';
import { ObservabilityPanelComponent } from '../features/observability-panel/observability-panel.component';

@Component({
  standalone: true,
  imports: [ObservabilityPanelComponent],
  template: `<app-observability-panel />`,
})
export class ObservabilityPageComponent {}
