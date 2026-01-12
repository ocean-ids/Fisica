import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Asignacion } from '../models';

@Injectable({
  providedIn: 'root'
})
export class AsignacionService {

  constructor(private apiService: ApiService) { }

  getAsignaciones(): Observable<Asignacion[]> {
    return this.apiService.get<Asignacion[]>('/asignaciones/');
  }

  getAsignacion(id: number): Observable<Asignacion> {
    return this.apiService.get<Asignacion>(`/asignaciones/${id}/`);
  }

  createAsignacion(asignacion: Asignacion): Observable<Asignacion> {
    return this.apiService.post<Asignacion>('/asignaciones/', asignacion);
  }

  updateAsignacion(id: number, asignacion: Asignacion): Observable<Asignacion> {
    return this.apiService.put<Asignacion>(`/asignaciones/${id}/`, asignacion);
  }

  deleteAsignacion(id: number): Observable<any> {
    return this.apiService.delete(`/asignaciones/${id}/`);
  }
}
