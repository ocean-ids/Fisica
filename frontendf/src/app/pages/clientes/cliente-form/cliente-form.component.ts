import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatTabsModule } from '@angular/material/tabs';
import { Cliente } from '../../../models/cliente.model';
import { ClienteService } from '../../../services/cliente.service';
import { UbicacionService } from '../../../services/ubicacion.service';

@Component({
  selector: 'app-cliente-form',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule, MatDialogModule, MatFormFieldModule,
    MatInputModule, MatButtonModule, MatSelectModule, MatCheckboxModule, MatTabsModule
  ],
  templateUrl: './cliente-form.component.html',
  styleUrl: './cliente-form.component.css'
})
export class ClienteFormComponent implements OnInit {
  clienteForm!: FormGroup;
  provincias: any[] = [];
  cantones: any[] = [];

  sizes = [
    { v: 'PEQUENO', l: 'Pequeño' }, { v: 'MEDIANO', l: 'Mediano' },
    { v: 'GRANDE', l: 'Grande' }, { v: 'OFICINA', l: 'Oficina' },
  ];
  estados = [{ v: 'ACTIVO', l: 'Activo' }, { v: 'INACTIVO', l: 'Inactivo' }];
  tiposId = [
    { v: 'RUC', l: 'RUC' }, { v: 'CEDULA', l: 'Cédula' }, { v: 'PASAPORTE', l: 'Pasaporte' },
  ];
  tiposCliente = [{ v: 'JURIDICA', l: 'Jurídica' }, { v: 'NATURAL', l: 'Natural' }];
  sexos = [{ v: 'MASCULINO', l: 'Masculino' }, { v: 'FEMENINO', l: 'Femenino' }];
  estadosCiviles = [
    { v: 'SOLTERO', l: 'Soltero' },
    { v: 'CASADO', l: 'Casado' },
    { v: 'DIVORCIADO', l: 'Divorciado' },
    { v: 'UNION LIBRE', l: 'Unión Libre' },
    { v: 'VIUDO', l: 'Viudo' },
  ];

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<ClienteFormComponent>,
    private clienteService: ClienteService,
    private ubicacionService: UbicacionService,
    @Inject(MAT_DIALOG_DATA) public cliente: Cliente
  ) {}

  ngOnInit(): void {
    const c: any = this.cliente || {};
    this.clienteForm = this.fb.group({
      // Identificación
      razon_social: [c.razon_social || '', Validators.required],
      nombre_comercial: [c.nombre_comercial || '', Validators.required],
      ruc: [c.ruc || '', [Validators.pattern(/^\d{10}(\d{3})?$/), Validators.minLength(10), Validators.maxLength(13)]],
      codigo_erp: [c.codigo_erp || ''],
      tipo_id: [c.tipo_id || ''],
      tipo_cliente: [c.tipo_cliente || ''],
      size: [c.size || 'MEDIANO', Validators.required],
      estado: [c.estado || 'ACTIVO'],
      fecha_ingreso: [c.fecha_ingreso || null],
      fecha_retiro: [c.fecha_retiro || null],
      ultima_venta: [c.ultima_venta || null],
      // Ubicación
      provincia: [c.provincia ?? null],
      canton: [c.canton ?? null],
      ciudad: [c.ciudad || ''],
      parroquia: [c.parroquia || ''],
      direccion_comercial: [c.direccion_comercial || ''],
      sector: [c.sector || ''],
      sexo: [c.sexo || ''],
      estado_civil: [c.estado_civil || ''],
      // Contacto
      telefono: [c.telefono || ''],
      telefono2: [c.telefono2 || ''],
      fax: [c.fax || ''],
      email: [c.email || ''],
      email_adicional: [c.email_adicional || ''],
      copia_correo_1: [c.copia_correo_1 || ''],
      copia_correo_2: [c.copia_correo_2 || ''],
      copia_correo_3: [c.copia_correo_3 || ''],
      copia_correo_4: [c.copia_correo_4 || ''],
      copia_correo_5: [c.copia_correo_5 || ''],
      // Comercial / crédito
      vendedor: [c.vendedor || ''],
      rep_legal: [c.rep_legal || ''],
      plazo_max: [c.plazo_max ?? 0],
      desc_vta: [c.desc_vta ?? 0],
      cupo: [c.cupo ?? 0],
      cod_agrupacion: [c.cod_agrupacion || ''],
      valoracion_custodias: [c.valoracion_custodias || ''],
      tipo_precio: [c.tipo_precio || ''],
      valor_puesto: [c.valor_puesto ?? 0],
      forma_pago: [c.forma_pago || ''],
      origen_ingreso: [c.origen_ingreso || ''],
      zona: [c.zona || ''],
      control_cupo: [c.control_cupo ?? false],
      requiere_correo: [c.requiere_correo ?? false],
      controla_factura_reverso: [c.controla_factura_reverso ?? false],
      // Contable
      cuenta_contable: [c.cuenta_contable || ''],
      cod_area: [c.cod_area || ''],
      cod_rol: [c.cod_rol || ''],
      paga_iva: [c.paga_iva ?? true],
      observaciones: [c.observaciones || ''],
    });

    this.loadProvincias();

    // Al editar, cargar el cliente completo (la lista solo trae campos básicos).
    if (c.id) {
      this.clienteService.getCliente(c.id).subscribe({
        next: (full: any) => {
          this.clienteForm.patchValue(full);
          if (full?.provincia) this.onProvinciaChange(full.canton ?? null);
        },
        error: () => {}
      });
    }
  }

  private loadProvincias(): void {
    this.ubicacionService.getProvincias().subscribe({
      next: (list: any[]) => {
        this.provincias = list || [];
        const provId = this.clienteForm.get('provincia')?.value;
        if (provId) this.onProvinciaChange(this.clienteForm.get('canton')?.value ?? null);
      },
      error: () => { this.provincias = []; }
    });
  }

  onProvinciaChange(keepCantonId: number | null = null): void {
    const provId = this.clienteForm.get('provincia')?.value;
    if (!provId) {
      this.cantones = [];
      this.clienteForm.get('canton')?.setValue(null);
      return;
    }
    this.ubicacionService.getCantones(provId).subscribe({
      next: (cants: any[]) => {
        this.cantones = cants || [];
        const current = keepCantonId ?? this.clienteForm.get('canton')?.value;
        if (current && this.cantones.find((x: any) => x.id === current)) {
          this.clienteForm.get('canton')?.setValue(current);
        } else if (keepCantonId === null) {
          this.clienteForm.get('canton')?.setValue(null);
        }
      },
      error: () => { this.cantones = []; }
    });
  }

  onSubmit(): void {
    if (this.clienteForm.valid) {
      this.dialogRef.close(this.clienteForm.value);
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
