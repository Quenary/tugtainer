import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SettingsForm } from './settings-form';

describe('SettingsForm', () => {
  let component: SettingsForm;
  let fixture: ComponentFixture<SettingsForm>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SettingsForm]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SettingsForm);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
