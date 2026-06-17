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
  private initialCantonName: string | null = null;
  private initialProvinciaName: string | null = null;
  tipos: Persona['tipo'][] = [
    'FIJOS',
    'RETEN',
    'CUSTODIO',
    'EVENTUAL',
    'SACAFRANCO',
    'SACAVACACIONES',
    'SUPERVISOR ZONAL',
    'SUPERVISOR EVENTUAL',
    'SUPERVISOR MOTORIZADO',
    'SUPERVISOR DE ACOMPAÑAMIENTO',
    'OPERADOR CENTRO CONTROL',
    'SUPERVISOR CENTRO CONTROL',
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
    this.initialCanton = (this.persona?.canton as any) ?? null;
    this.initialCantonName = (this.persona?.canton_nombre || '').trim().toUpperCase() || null;
    this.initialProvinciaName = (this.persona?.provincia_nombre || '').trim().toUpperCase() || null;

    const applyInitialProvincia = () => {
      const storedProvId = this.persona?.provincia ?? null;
      const provFoundById = storedProvId
        ? this.provincias.find((x: any) => x.id === storedProvId)
        : null;
      const provFoundByName = this.initialProvinciaName
        ? this.provincias.find((x: any) => (x.nombre || '').toUpperCase() === this.initialProvinciaName)
        : null;
      const provFound = provFoundById || provFoundByName;
      if (provFound) {
        this.personaForm.get('provincia')?.setValue(provFound.id);
        this.onProvinciaChange();
      }
    };

    this.useStaticProvincias = false;
    this.ubicacionService.getProvincias().subscribe({
      next: (list) => {
        this.provincias = list || [];
        applyInitialProvincia();
      },
      error: () => {
        this.useStaticProvincias = true;
        this.provincias = this.provinciasService.getProvinciasSync();
        applyInitialProvincia();
      }
    });
  }

  private afterCantonesLoaded(): void {
    if (this.initialCanton || this.initialCantonName) {
      const foundById = this.initialCanton
        ? this.cantones.find((x: any) => x.id === this.initialCanton)
        : null;
      const foundByName = this.initialCantonName
        ? this.cantones.find((x: any) => (x.nombre || '').toUpperCase() === this.initialCantonName)
        : null;
      const found = foundById || foundByName;
      if (found) {
        this.personaForm.get('canton')?.setValue(found.id);
        this.initialCanton = null;
        this.initialCantonName = null;
        return;
      }
      this.initialCanton = null;
      this.initialCantonName = null;
    }
    const current = this.personaForm.get('canton')?.value;
    if (current && this.cantones.find((x: any) => x.id === current)) {
      return;
    }
    this.personaForm.get('canton')?.setValue(null);
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
