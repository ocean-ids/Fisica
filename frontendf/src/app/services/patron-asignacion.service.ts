import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PatronAsignacion } from '../models/asignacion.model';

@Injectable({
  providedIn: 'root'
})
export class PatronAsignacionService {
  private apiUrl = 'http://localhost:8000/api/patrones/';

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  obtenerPatrones(): Observable<PatronAsignacion[]> {
    return this.http.get<PatronAsignacion[]>(this.apiUrl, { headers: this.getHeaders() });
  }

  crearPatron(patron: PatronAsignacion): Observable<PatronAsignacion> {
    return this.http.post<PatronAsignacion>(this.apiUrl, patron, { headers: this.getHeaders() });
  }

  actualizarPatron(id: number, patron: PatronAsignacion): Observable<PatronAsignacion> {
    return this.http.put<PatronAsignacion>(`${this.apiUrl}${id}/`, patron, { headers: this.getHeaders() });
  }

  eliminarPatron(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}${id}/`, { headers: this.getHeaders() });
  }

  getSacafrancos(weekStart: string, day: string, puestoId?: number) {
    const params = new URLSearchParams();
    if (weekStart) params.set('week_start', weekStart);
    if (day) params.set('day', day);
    if (puestoId) params.set('puesto_id', String(puestoId));
    const url = `http://localhost:8000/api/personas/sacafrancos/?${params.toString()}`;
    return this.http.get<any[]>(url, { headers: this.getHeaders() });
  }

  asignarSacafranco(payload: any) {
    const url = `http://localhost:8000/api/personas/sacafrancos/assign/`;
    return this.http.post<any>(url, payload, { headers: this.getHeaders() });
  }

  desasignarSacafranco(payload: any) {
    const url = `http://localhost:8000/api/personas/sacafrancos/unassign/`;
    return this.http.post<any>(url, payload, { headers: this.getHeaders() });
  }
}