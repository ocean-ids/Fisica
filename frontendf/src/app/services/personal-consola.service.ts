import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';
import { PersonalConsola } from '../models';

@Injectable({
  providedIn: 'root'
})
export class PersonalConsolaService {

  constructor(private api: ApiService) { }

  getPersonalConsola(params?: any): Observable<PersonalConsola[]> {
    return this.api.get<PersonalConsola[]>('/personal-consola/', params);
  }

  createPersonalConsola(payload: PersonalConsola): Observable<PersonalConsola> {
    return this.api.post<PersonalConsola>('/personal-consola/crear/', payload);
  }

  updatePersonalConsola(id: number, payload: PersonalConsola): Observable<PersonalConsola> {
    return this.api.put<PersonalConsola>(`/personal-consola/${id}/`, payload);
  }

  deletePersonalConsola(id: number): Observable<any> {
    return this.api.delete(`/personal-consola/${id}/eliminar/`);
  }

}
