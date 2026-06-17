import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Instalacion } from '../models';

@Injectable({
  providedIn: 'root'
})
export class InstalacionService {
  constructor(private apiService: ApiService){}
  
  getInstalaciones(params?: any): Observable<Instalacion[]> {
    return this.apiService.get<Instalacion[]>('/instalaciones/', params);
  }

  getInstalacion(id: number): Observable<Instalacion>{
    return this.apiService.get<Instalacion>(`/instalaciones/${id}/`);
  }

  createInstalacion(instalacion: any): Observable<any>{
    return this.apiService.post<any>('/crear-instalacion/', instalacion);
  }

  updateInstalacion(id: number, instalacion:any): Observable<any>{
    return this.apiService.put<any>(`/actualizar-instalacion/${id}/`, instalacion);
  }

  deleteInstalacion(id: number): Observable<any>{
    return this.apiService.delete(`/eliminar-instalacion/${id}/`);
  }
  
}
