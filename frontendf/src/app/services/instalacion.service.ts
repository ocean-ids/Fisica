import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Instalacion } from '../models';

@Injectable({
  providedIn: 'root'
})
export class InstalacionService {

  constructor(private apiService: ApiService) { }

  getInstalaciones(): Observable<Instalacion[]> {
    return this.apiService.get<Instalacion[]>('/instalaciones/');
  }

  getInstalacion(id: number): Observable<Instalacion> {
    return this.apiService.get<Instalacion>(`/instalaciones/${id}/`);
  }

  createInstalacion(instalacion: Instalacion): Observable<Instalacion> {
    return this.apiService.post<Instalacion>('/instalaciones/', instalacion);
  }

  updateInstalacion(id: number, instalacion: Instalacion): Observable<Instalacion> {
    return this.apiService.put<Instalacion>(`/instalaciones/${id}/`, instalacion);
  }

  deleteInstalacion(id: number): Observable<any> {
    return this.apiService.delete(`/instalaciones/${id}/`);
  }
}
