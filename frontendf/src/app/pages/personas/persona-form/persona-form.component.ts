import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { Persona } from '../../../models/persona.model';
import { UbicacionService } from '../../../services/ubicacion.service';
import { ProvinciasService } from '../../../services/provincias.service';
import { Province, City } from '../../../data/provincias';

@Component({
  selector: 'app-persona-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule
  ],
  templateUrl: './persona-form.component.html',
  styleUrl: './persona-form.component.css'
})
export class PersonaFormComponent implements OnInit {
  personaForm!: FormGroup;
  provincias: (any | Province)[] = [];
  cantones: (any | City)[] = [];
  private useStaticProvincias = false;
  private initialCanton: string | null = null;
  tipos: Persona['tipo'][] = [
    'FIJOS',
    'RETENES',
    'CUSTODIO',
    'EVENTUALES',
    'SACAFRANCO',
    'SACAVACACIONES',
    'SUPERVISOR ZONAL',
    'SUPERVISOR MOTORIZADO',
    'SUPERVISOR DE ACOMPAÑAMIENTO',
  ];

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<PersonaFormComponent>,
    @Inject(MAT_DIALOG_DATA) public persona: Persona,
    private ubicacionService: UbicacionService,
    private provinciasService: ProvinciasService
  ) {}

  ngOnInit(): void {
    this.personaForm = this.fb.group({
      nombres: [this.persona?.nombres || '', Validators.required],
      apellidos: [this.persona?.apellidos || '', Validators.required],
      cedula: [this.persona?.cedula || '', [Validators.required, Validators.pattern('^[0-9]{1,10}$'), Validators.maxLength(10)]],
      provincia: [this.persona?.provincia ?? null],
      canton: [this.persona?.canton ?? null],
      tipo: [this.persona?.tipo ?? 'FIJOS', Validators.required]
    });

    this.loadProvincias();
  }

  onProvinciaChange(): void {
    const provinciaId = this.personaForm.get('provincia')?.value;
    if (!provinciaId) {
      this.cantones = [];
      this.personaForm.get('canton')?.setValue(null);
      return;
    }
    if (this.useStaticProvincias) {
      const prov = (this.provincias as Province[]).find(x => x.id === provinciaId);
      this.cantones = prov ? prov.ciudades : [];
      this.afterCantonesLoaded();
    } else {
      this.ubicacionService.getCantones(provinciaId).subscribe((cants: any[]) => {
        this.cantones = cants || [];
        this.afterCantonesLoaded();
      });
    }
  }

  private loadProvincias(): void {
    this.useStaticProvincias = true;
    this.provincias = this.provinciasService.getProvinciasSync();
    this.initialCanton = (this.persona?.canton as any) ?? null;
    const storedProv = this.persona?.provincia ?? null;
    if (storedProv) {
      const provFound = this.provincias.find((x: any) => x.id === storedProv);
      if (provFound) {
        this.personaForm.get('provincia')?.setValue(provFound.id);
        this.onProvinciaChange();
      }
    }
  }

  private afterCantonesLoaded(): void {
    if (this.initialCanton) {
      const found = this.cantones.find((x: any) => x.id === this.initialCanton);
      if (found) {
        this.personaForm.get('canton')?.setValue(found.id);
        this.initialCanton = null;
        return;
      }
      this.initialCanton = null;
    }
    const current = this.personaForm.get('canton')?.value;
    if (current && this.cantones.find((x: any) => x.id === current)) {
      return;
    }
    if (this.cantones.length > 0) {
      this.personaForm.get('canton')?.setValue(this.cantones[0].id);
    } else {
      this.personaForm.get('canton')?.setValue(null);
    }
  }

  onSubmit(): void {
    if (this.personaForm.valid) {
      this.dialogRef.close(this.personaForm.value);
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
