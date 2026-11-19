import { Routes } from '@angular/router';
import { AgentPageComponent } from './pages/agent-page.component';
import { KnowledgePageComponent } from './pages/knowledge-page.component';
import { ObservabilityPageComponent } from './pages/observability-page.component';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'agent' },
  { path: 'agent', component: AgentPageComponent },
  { path: 'knowledge', component: KnowledgePageComponent },
  { path: 'observability', component: ObservabilityPageComponent },
  { path: '**', redirectTo: 'agent' },
];
