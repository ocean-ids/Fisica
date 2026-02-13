import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { from, Observable } from 'rxjs';
import { Persona } from '../models';

@Injectable({
  providedIn: 'root'
})
export class PersonaService {

  constructor(private apiService: ApiService) { }

  getPersonas(params?: { q?: string; tipo?: string }): Observable<Persona[]>{
    return this.apiService.get<Persona[]>('/personas/', params);
  }

  getPersona(id: number): Observable<Persona>{
    return this.apiService.get<Persona>(`/personas/${id}/`);
  }

  createPersona(persona: Persona): Observable<Persona>{
    return this.apiService.post<Persona>('/crear-persona/', persona);
  }

  updatePersona(id: number, persona: Persona): Observable<Persona>{
    return this.apiService.put<Persona>(`/actualizar-persona/${id}/`, persona);
  }

  deletePersona(id: number): Observable<any>{
    return this.apiService.delete(`/eliminar-persona/${id}/`);
  }

  disablePersona(id: number): Observable<any>{
    return this.apiService.post(`/disable-persona/${id}/`, {});
  }

  enablePersona(id: number): Observable<any>{
    return this.apiService.post(`/enable-persona/${id}/`, {});
  }

  importPersonas(file: File, dryRun = false) {
    const formData = new FormData();
    formData.append('file', file);
    const endpoint = `/importar-personas/${dryRun ? '?dry_run=true' : ''}`;
    return this.apiService.post<any>(endpoint, formData);
  }

}
