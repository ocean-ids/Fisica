import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatRadioModule } from '@angular/material/radio';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatTabsModule } from '@angular/material/tabs';
import { Persona } from '../../../models/persona.model';
import { UbicacionService } from '../../../services/ubicacion.service';
import { ProvinciasService } from '../../../services/provincias.service';
import { ClienteService } from '../../../services/cliente.service';
import { PersonaService } from '../../../services/persona.service';
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
    MatSelectModule,
    MatRadioModule,
    MatCheckboxModule,
    MatTabsModule
  ],
  templateUrl: './persona-form.component.html',
  styleUrl: './persona-form.component.css'
})
export class PersonaFormComponent implements OnInit {
  personaForm!: FormGroup;
  provincias: (any | Province)[] = [];
  cantones: (any | City)[] = [];
  clientes: { id: number; nombre: string }[] = [];
  fotoFile: File | null = null;
  fotoPreview: string | null = null;
  sexos = [{ v: 'MASCULINO', l: 'Masculino' }, { v: 'FEMENINO', l: 'Femenino' }];
  estadosCiviles = [{ v: 'SOLTERO', l: 'Soltero' }, { v: 'CASADO', l: 'Casado' }];
  tiposEmpleado = [{ v: 'EMPLEADO', l: 'Empleado' }, { v: 'OBRERO', l: 'Obrero' }, { v: 'OPERADOR', l: 'Operador' }];
  regiones = ['SIERRA', 'COSTA'];
  unidadesNegocio = ['SEGURIDAD FISICA'];
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
    private provinciasService: ProvinciasService,
    private clienteService: ClienteService,
    private personaService: PersonaService
  ) {}

  ngOnInit(): void {
    const p: any = this.persona || {};
    this.personaForm = this.fb.group({
      // Datos base de la app
      cedula: [p.cedula || '', [Validators.required, Validators.pattern('^[0-9]{1,10}$'), Validators.maxLength(10)]],
      nombres: [p.nombres || '', Validators.required],
      apellidos: [p.apellidos || '', Validators.required],
      tipo: [p.tipo ?? 'FIJOS', Validators.required],
      provincia: [p.provincia ?? null],
      canton: [p.canton ?? null],
      is_active: [p.is_active ?? true],
      // Datos del ERP
      codigo_erp: [p.codigo_erp || ''],
      centro_costo: [p.centro_costo || ''],
      sexo: [p.sexo || ''],
      estatura: [p.estatura ?? null],
      lugar_nacimiento: [p.lugar_nacimiento || ''],
      fecha_nacimiento: [p.fecha_nacimiento || null],
      direccion: [p.direccion || ''],
      parroquia: [p.parroquia || ''],
      estado_civil: [p.estado_civil || ''],
      telefono: [p.telefono || '', Validators.pattern('^[0-9]*$')],
      conyuge: [p.conyuge || ''],
      nacionalidad: [p.nacionalidad || ''],
      cliente: [p.cliente ?? null],
      unidad_negocio: [p.unidad_negocio || 'SEGURIDAD FISICA'],
      tipo_empleado: [p.tipo_empleado || ''],
      cargo: [p.cargo || 'AGENTE DE SEGURIDAD G'],
      fecha_ingreso: [p.fecha_ingreso || null],
      fecha_salida: [p.fecha_salida || null],
      forma_pago: [p.forma_pago || ''],
      numero_afiliacion: [p.numero_afiliacion || ''],
      numero_contrato: [p.numero_contrato || ''],
      actividad: [p.actividad || ''],
      seccion: [p.seccion || ''],
      departamento: [p.departamento || ''],
      perfil: [p.perfil || ''],
      fecha_pago_liquidacion: [p.fecha_pago_liquidacion || null],
      motivo_salida: [p.motivo_salida || ''],
      correo_personal: [p.correo_personal || ''],
      region: [p.region || ''],
      gypaseg: [p.gypaseg ?? false],
      affis: [p.affis ?? false],
      pbip: [p.pbip ?? false],
      // Nómina (Ingresos / Descuentos) — pestaña "Ingresos Dctos."
      nomina: this.fb.group({
        // Sueldo y Beneficios de Ley
        sueldo: [0], desc_genesis: [0], bonificacion: [0], transporte: [0], compensacion: [0],
        horas_25: [0], horas_50: [0], horas_100: [0],
        pagar_fondo_reserva: [false], observaciones: [''],
        // Acumulados de Beneficios Sociales
        decimo_tercer: [0], decimo_cuarto: [0], vacaciones: [0], fondo_reserva: [0],
        pagar_rol_10mo_3ero: [false], pagar_rol_10mo_4to: [false], pagar_rol_vacaciones: [false],
        desc_aporte_conyuge: [false], giro_contable_liquidacion: [false],
        numero_liquidacion_ministerio: [''],
        // Rol Extra
        moviliza: [0], lunch: [0], anticipo_22: [0], viaticos: [0], descuento: [0], ingreso_extra: [0],
        concepto: [''],
        // Subsidio
        subsidio_enfermedad: [false], subsidio_enfermedad_pct: [0],
        subsidio_accidente: [false], subsidio_accidente_pct: [0],
        subsidio_maternidad: [false], subsidio_maternidad_pct: [0],
      }),
    });

    // Al editar, cargar la nómina existente del empleado.
    if (p.id) {
      this.personaService.getNomina(p.id).subscribe({
        next: (n) => { if (n) this.personaForm.get('nomina')?.patchValue(n); },
        error: () => {}
      });
    }

    this.loadProvincias();
    this.clienteService.getClientes().subscribe({
      next: (list: any[]) => { this.clientes = (list || []).map(c => ({ id: c.id, nombre: c.razon_social || c.nombre_comercial })); },
      error: () => { this.clientes = []; }
    });
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

  soloNumeros(event: KeyboardEvent): void {
    // Permite teclas de control (Backspace, Tab, flechas, Supr, etc.) y atajos
    if (event.key.length > 1 || event.ctrlKey || event.metaKey) {
      return;
    }
    // Bloquea cualquier caracter que no sea digito
    if (!/[0-9]/.test(event.key)) {
      event.preventDefault();
    }
  }

  onFotoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files && input.files.length ? input.files[0] : null;
    this.fotoFile = file;
    if (file) {
      const reader = new FileReader();
      reader.onload = () => { this.fotoPreview = reader.result as string; };
      reader.readAsDataURL(file);
    }
  }

  onSubmit(): void {
    if (this.personaForm.valid) {
      this.dialogRef.close({ ...this.personaForm.value, _fotoFile: this.fotoFile });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
