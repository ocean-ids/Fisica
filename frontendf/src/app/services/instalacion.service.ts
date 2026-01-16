import { Injectable } from '@angular/core';
import { Observable, of, tap } from 'rxjs';
import { ApiService } from './api.service';
import { Instalacion } from '../models';

@Injectable({
  providedIn: 'root'
})
export class InstalacionService {
  private cache: Instalacion[] | null = null;

  constructor(private apiService: ApiService){}
  
  getInstalaciones(forceRefresh: boolean = false): Observable<Instalacion[]>{
    if (!forceRefresh && this.cache) {
      return of(this.cache);
    }
    return this.apiService.get<Instalacion[]>('/instalaciones/').pipe(
      tap(data => this.cache = data)
    );
  }

  getInstalacion(id: number): Observable<Instalacion>{
    return this.apiService.get<Instalacion>(`/instalaciones/${id}/`);
  }

  createInstalacion(instalacion: any): Observable<any>{
    this.cache = null; // Invalidar caché
    return this.apiService.post<any>('/crear-instalacion/', instalacion);
  }

  updateInstalacion(id: number, instalacion:any): Observable<any>{
    this.cache = null; // Invalidar caché
    return this.apiService.put<any>(`/actualizar-instalacion/${id}/`, instalacion);
  }

  deleteInstalacion(id: number): Observable<any>{
    this.cache = null; // Invalidar caché
    return this.apiService.delete(`/eliminar-instalacion/${id}/`);
  }
  
}
