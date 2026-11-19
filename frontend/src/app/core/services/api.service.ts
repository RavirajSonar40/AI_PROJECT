import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  AgentRequest,
  AgentResponse,
  AgentResumeRequest,
  DocumentItem,
  EvaluationDataset,
  EvaluationRun,
  EvaluationRunDetail,
  HealthReadyResponse,
  ObservabilityOverview,
  ObservabilityRequest,
  PlanRequest,
  PlanResponse,
  PlanResumeRequest,
  RecommendationFeedbackRequest,
  RecommendationHistory,
  RecommendationResponse,
} from '../models/api.models';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private readonly baseUrl = window.__env?.API_URL || '/api';

  constructor(private readonly http: HttpClient) {}

  listDocuments(): Observable<DocumentItem[]> {
    return this.http.get<DocumentItem[]>(`${this.baseUrl}/documents`);
  }

  uploadDocument(file: File): Observable<DocumentItem> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<DocumentItem>(`${this.baseUrl}/documents/upload`, formData);
  }

  askAgent(request: AgentRequest): Observable<AgentResponse> {
    return this.http.post<AgentResponse>(`${this.baseUrl}/agent/ask`, request);
  }

  resumeAgent(request: AgentResumeRequest): Observable<AgentResponse> {
    return this.http.post<AgentResponse>(`${this.baseUrl}/agent/resume`, request);
  }

  planTask(request: PlanRequest): Observable<PlanResponse> {
    return this.http.post<PlanResponse>(`${this.baseUrl}/agent/plan`, request);
  }

  resumePlan(request: PlanResumeRequest): Observable<PlanResponse> {
    return this.http.post<PlanResponse>(`${this.baseUrl}/agent/plan/resume`, request);
  }

  getRecommendations(
    userId: string,
    limit = 5,
    includeSeen = false,
  ): Observable<RecommendationResponse> {
    return this.http.post<RecommendationResponse>(`${this.baseUrl}/recommendations`, {
      user_id: userId,
      limit,
      include_seen: includeSeen,
    });
  }

  submitRecommendationFeedback(
    request: RecommendationFeedbackRequest,
  ): Observable<{ status: string }> {
    return this.http.post<{ status: string }>(
      `${this.baseUrl}/recommendations/feedback`,
      request,
    );
  }

  getRecommendationHistory(
    userId: string,
    limit = 10,
  ): Observable<RecommendationHistory> {
    return this.http.get<RecommendationHistory>(
      `${this.baseUrl}/recommendations/${encodeURIComponent(userId)}/history`,
      { params: { limit } },
    );
  }

  listEvaluationDatasets(): Observable<EvaluationDataset[]> {
    return this.http.get<EvaluationDataset[]>(`${this.baseUrl}/evaluation/datasets`);
  }

  runEvaluation(
    dataset: string,
    maxCases: number,
    pipelines?: string[],
  ): Observable<{ run_id: number; status: string; summary: unknown }> {
    return this.http.post<{ run_id: number; status: string; summary: unknown }>(
      `${this.baseUrl}/evaluation/runs`,
      {
        dataset,
        max_cases: maxCases,
        pipelines,
      },
    );
  }

  listEvaluationRuns(limit = 10): Observable<EvaluationRun[]> {
    return this.http.get<EvaluationRun[]>(`${this.baseUrl}/evaluation/runs`, {
      params: { limit },
    });
  }

  getEvaluationRun(runId: number): Observable<EvaluationRunDetail> {
    return this.http.get<EvaluationRunDetail>(`${this.baseUrl}/evaluation/runs/${runId}`);
  }

  getObservabilityOverview(hours = 24): Observable<ObservabilityOverview> {
    return this.http.get<ObservabilityOverview>(
      `${this.baseUrl}/observability/overview`,
      { params: { hours } },
    );
  }

  listObservabilityRequests(limit = 20): Observable<ObservabilityRequest[]> {
    return this.http.get<ObservabilityRequest[]>(
      `${this.baseUrl}/observability/requests`,
      { params: { limit } },
    );
  }

  getReadiness(): Observable<HealthReadyResponse> {
    return this.http.get<HealthReadyResponse>(`${this.baseUrl}/health/ready`);
  }
}
